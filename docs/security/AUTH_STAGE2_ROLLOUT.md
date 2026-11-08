# Etapa 2: reservas, locks e troca de versão

Status: alternativa pragmática autorizada e implementada: admissão distribuída e teto de verificações por processo. Validação PostgreSQL e comprovação da barreira de implantação continuam pendentes. Este documento não autoriza nem registra operações em infraestrutura ou dados reais.

## Limite atual da reserva

A admissão grava `login_attempts` antes da senha e encerra sua transação. O hash roda sincronicamente no worker da rota, dentro de semáforo compartilhado pelo verificador comum. Expirar `expira_em` só libera admissão distribuída: não encerra hash nem libera sua vaga local. Cancelar HTTP também não comprova que a thread parou.

São estados diferentes:

- Trabalho ativo: pode continuar usando CPU após cancelamento HTTP ou perda de comunicação.
- Requisição cancelada: não se deve liberar capacidade só porque o cliente desconectou ou a tarefa ASGI foi cancelada.
- Processo comprovadamente encerrado: o trabalho daquele processo acabou; suas reservas podem ser recuperadas sob coordenação.
- Reserva sem heartbeat: é suspeita de abandono, não prova de término do trabalho.

O teste `test_active_password_work_must_not_lose_capacity_when_lease_expires` configura capacidade local de dois, mantém duas verificações ativas e avança o relógio além da lease. A admissão distribuída pode recuperar registros, mas novas verificações recebem 503 de saturação local e o pico permanece dois. O teste passou após a correção, sem skip/expectedFailure. O teste antigo de admissão distribuída configura capacidade local de dois para continuar isolando o orçamento distribuído de dois, sem que o padrão local de um mascare essa verificação.

`AUTH_PASSWORD_MAX_CONCURRENCY` tem padrão um, validado entre 1 e 16 ao iniciar o processo. Aquisição não bloqueante rejeita saturação com 503 genérico/Retry-After=1, sem fila nova de espera por vaga. O finally está dentro da chamada síncrona e cobre verificação e eventual rehash, inclusive erros; não está no ciclo de vida da tarefa HTTP. `verify_password` e `verify_password_and_update` compartilham a capacidade, inclusive confirmação para exclusão. Geração independente em cadastro/reset fica fora desse teto; Argon2/bcrypt não foram enfraquecidos. Identidades inexistentes passam pela mesma decisão de saturação, retornando falha sem executar hash quando há vaga.

Depois do CAS de User e de eventual espera por esse lock, um UPDATE condicional consome a reserva ativa/não expirada na mesma transação de criação da sessão. Invalidação anterior, expiração ou cancelamento observado antes da autorização causam 503, rollback do upgrade e ausência de tokens/cookie. O consumo é o ponto de autorização; checagens do sinal de cancelamento também antecedem o commit, mas há uma janela entre a última checagem e o commit. Não há promessa de rollback ou revogação retroativa se o cancelamento concorrer com uma transação cuja autorização venceu. Desconexão do cliente nem sempre cancela a tarefa ASGI; em qualquer caso, ela não libera o semáforo do hash ainda ativo.

Trabalho travado pode ocupar uma vaga até terminar ou o processo ser efetivamente encerrado: não há hard timeout nem supervisor de subprocessos. Morte real do processo encerra suas threads; processos novos iniciam com capacidade nova, e registros antigos expiram nas janelas/lease existentes. O teto agregado é a soma das capacidades dos processos vivos; quantidade maior de workers/instâncias ou sobreposição durante deploy aumenta esse teto. Este mecanismo não limita as filas gerais de HTTP/threads/conexões. PostgreSQL compartilha admissão, não mede prova de término dos hashes remotos.

Alternativas analisadas antes da decisão:

| Opção | Garantia e custo |
|---|---|
| Heartbeat com fencing transacional antes de emitir sessão | Reduz expiração normal e pode impedir emissão após perda da reserva. Não limita estritamente hashes vivos durante pausa/partição; não atende sozinho ao teto estrito. |
| Reserva persistente até término real, com finalização pelo worker | Conservadora para simultaneidade, porém um crash prende vagas até recuperação operacional comprovada. Exige excluir reservas ativas do expurgo de 30 dias. Não atende à recuperação automática pedida. |
| Lock de banco mantido durante o hash | Ocupa conexões; no SQLite prolonga o bloqueio de escrita. Perda da conexão pode liberar lock sem encerrar hash. Não resolve sozinho o cenário de falha. |
| Hash em processo supervisionado, com coordenação de capacidade | Permite encerrar e confirmar término antes de liberar a vaga. Exige projetar ownership, comunicação, morte do supervisor e recuperação entre instâncias; TTL continua insuficiente como única prova. Mudança significativa sujeita a aprovação. |

Decisão posterior do usuário: implementar a alternativa pragmática descrita acima, com teto local e admissão distribuída, aceitando dependência do número real de processos. Nenhum subprocesso supervisionado, coordenador global, serviço externo ou schema adicional foi implementado.

## Resultados de login: revisão aditiva 20261107_02

A migração acrescenta `resultado` (String24 nullable) e `motivo_finalizacao` (String40 nullable). Não altera migrações anteriores nem executa backfill, recriação de tabela ou mudança de índices. As leituras continuam delimitadas pelos índices existentes de conta/IP/rota/tempo. Os motivos são códigos internos validados por enum, sem senha, token, mensagem de exceção ou novo dado pessoal.

| Resultado novo | Orçamento de falhas/admissão | Frequência geral |
|---|---|---|
| pendente | Ocupa provisoriamente enquanto reserva está viva e em execução | Conta |
| sucesso | Não consome falhas | Conta |
| credencial_rejeitada | Consome nas janelas originais | Conta |
| neutro | Não consome falhas; sucesso continua false | Conta |

Saturação/erro antes de qualquer rejeição conhecida, payload inválido, conta indisponível e reserva encerrada sem veredicto são neutros. Credenciais de identidade inexistente são rejeitadas pelo mesmo contrato genérico, sem revelar existência. Rate limiting continua anterior à reserva: não insere uma falsa falha nem renova a janela das tentativas bloqueadas.

O resultado é marcado explicitamente pela rota, antes de auditoria/commit. Rejeição já constatada sobrevive a erro, cancelamento ou expiração posteriores; o motivo pode indicar `erro_apos_rejeicao` ou `interrompida_apos_rejeicao`. Assim, não se presume que todo HTTP 503 seja equivalente: saturação sem verificação é neutra; erro depois de rejeição real preserva o veredicto. Cancelamento que finaliza a reserva antes de existir veredicto fica neutro e não pode ser sobrescrito por conclusão tardia.

`finish` faz um único UPDATE condicionado a resultado=pendente. Chamadas repetidas, inclusive concorrentes, têm somente um vencedor. Reservas expiradas/invalidadas sem rejeição conhecida finalizam neutras. Claim de login exige resultado pendente e reserva viva; grava sucesso/motivo na mesma transação de User e RefreshToken. Rollback desfaz esse sucesso provisório; o middleware pode então finalizar neutro. Sucesso já confirmado não é sobrescrito por erro tardio de resposta ou nova finalização.

Resultado NULL identifica todos os registros legados, inclusive reservas antigas: preserva-se a leitura binária anterior e suas janelas. Não há evidência para distinguir senha incorreta de indisponibilidade no histórico; manter essa interpretação pode conservar temporariamente um bloqueio antigo até sua janela expirar. Não é aplicada retroativamente a nova classificação a dados desconhecidos.

## Ordem de locks após classificação

| Fluxo | Ordem relevante |
|---|---|
| Login válido | CAS de User → criação de RefreshToken → commit |
| Refresh/replay | User → releitura do RefreshToken → rotação/revogação → commit |
| Logout | User → revogação da família de RefreshToken → commit |
| Bloqueio | User → revogação de RefreshToken → alteração do usuário → commit |
| Reset | leitura inicial do token → User → consumo condicional de PasswordResetToken → revogação de outros tokens/RefreshToken → commit |
| Exclusão | User, adquirido pelo helper de revogação, antes de RefreshToken e PasswordResetToken; administradores já adquirem locks de User em ordem de ID |

A correção move a primeira aquisição de User do reset para antes de qualquer UPDATE do token. Após esperar, recalcula o instante atual e o UPDATE condicional revalida validade e uso único; se a exclusão removeu o token ou ele expirou durante a espera, a operação retorna 400 e faz rollback. O helper posterior reutiliza o lock da mesma transação. Não foram adicionadas consultas em todas as requisições.

O teste SQLite comprova a ordem de execução e os contratos de reset, não um deadlock PostgreSQL. O teste PostgreSQL pausa reset antes de adquirir User, deixa exclusão adquirir User e exige que ambos terminem sem ciclo: exclusão 200 e reset 400. Somente deve rodar no banco descartável local explicitamente configurado pelo harness; sem esse banco fica ignorado.

## Evidência de sobreposição permitida

`render.yaml` declara serviço web sem disco persistente, `/ready` como health check e `python -m app.render_start` como start. Não declara barreira de exclusividade entre releases. O startup executa Alembic, confere revisão e inicia Uvicorn; não encerra instâncias anteriores. Sem `--workers`, Uvicorn usa `WEB_CONCURRENCY` se configurado, ou seu padrão de um worker. A contagem real de instâncias e overrides no Dashboard não foi consultada.

O Render documenta a criação da instância nova enquanto a anterior recebe tráfego, seguida de troca de tráfego e encerramento posterior. Portanto, mesmo um worker por instância pode coexistir com a versão anterior; múltiplas instâncias ampliam a janela. Aditividade da migração e readiness não eliminam essa sobreposição. Fontes públicas: [Render: zero-downtime deploys](https://render.com/docs/deploys#zero-downtime-deploys), [Uvicorn: workers](https://uvicorn.dev/settings/#production).

Reprodução anterior em SQLite: o corpo do logout de d4850cd9, executado sobre esquema novo após rotação T1→T2, retorna sucesso para T1 e deixa T2 renovável com HTTP 200. A correção depende de todos os emissores/revogadores participarem do protocolo novo.

## Procedimento proposto, dependente de autorização operacional

1. **Barreiras antes da janela.** Concluir a validação da capacidade local, executar os testes PostgreSQL descartáveis e aprovar o artefato exato. Inventariar serviços, instâncias, workers, overrides e todos os caminhos públicos/internos até a API. Confirmar a origem confiável do IP e que o domínio `onrender.com` ou outro acesso direto não contorna a manutenção. Não tratar header sintaticamente válido como autenticação do proxy.
2. **Preparar exclusividade verificável.** Com autorização específica, impedir deploys automáticos/concorrentes e fechar o tráfego na borda para toda a API durante a janela, preservando acesso restrito de verificação. Manutenção só no frontend é insuficiente. O repositório não implementa essa barreira: é necessário confirmar um mecanismo suportado pelo serviço/plano antes de iniciar. Se não for possível comprová-lo, não prosseguir; avaliar uma estratégia de compatibilidade entre releases ou serviço isolado, ambos sujeitos a autorização própria.
3. **Drenar e encerrar a versão anterior.** Bloquear novas requisições antes de drenar as existentes. Aguardar ou encerrar de forma controlada os processos antigos e confirmar que todos terminaram, inclusive workers filhos, emissores de tokens e processos mantidos em outra instância. Tempo decorrido, `/ready`, deploy marcado live e Restart Service isoladamente não provam essa condição. Não presumir que suspensão seguida de resume inicia o commit novo: confirmar o mecanismo e o artefato antes da operação.
4. **Tratar sessões emitidas anteriormente.** Depois do último emissor antigo encerrar, solicitar autorização específica para revogar, em transação, os refresh tokens ainda ativos, mantendo o histórico. Isso encerra também sucessores órfãos de logouts antigos, que só parar os workers não corrige. Implica novo login para todos os usuários. Se a revogação não for aprovada, registrar que sessões órfãs anteriores podem permanecer renováveis; não declarar saneamento retroativo.
5. **Migrar uma única vez.** Com workers antigos encerrados e admissão fechada, um processo de release com o artefato novo executa `python -m alembic upgrade head`, a partir de `backend`, e verifica `20261107_02`. Não imprimir a conexão nem dados. Não usar stamp/create_all, downgrade ou migrações simultâneas. Revisões históricas e dados existentes são preservados. Instâncias antigas podem inserir NULL nas novas colunas, mas não participam da classificação nova: a compatibilidade estrutural não autoriza versões mistas.
6. **Inicializar somente a versão nova.** Iniciar processos com o artefato aprovado; o `app.render_start` verificará novamente a revisão. Confirmar versão, ausência dos processos antigos, mesma SECRET_KEY e política LOGIN_RATE_* em todas as instâncias, relógios sincronizados e revisão correta. Só então iniciar instâncias adicionais. Ainda manter manutenção.
7. **Verificar antes de reabrir.** Com contas descartáveis autorizadas, verificar login, atributos de cookie/Origin, rotação, logout com token anterior e rejeição do sucessor, reset, bloqueio e limites 429/Retry-After. Verificar caminhos diretos e ausência de registros sensíveis. Testes de concorrência permanecem restritos ao PostgreSQL descartável, sem carga em serviço publicado. Reabrir tráfego apenas após as barreiras e verificações estarem demonstradas.
8. **Falha durante a janela.** Manter manutenção e nenhum worker incompatível atendendo; corrigir para frente. Não executar rollback automático para o artefato antigo: ele não conhece a revisão nova e não participa dos locks novos. Qualquer recuperação precisa confirmar artefato/esquema/protocolo compatíveis e preservar histórico.

Cookies de respostas já enviadas podem chegar tardiamente e reaparecer no navegador mesmo após parar workers. Com revogação aprovada após o encerramento de todos os emissores antigos, esses cookies não renovam sessão. Access JWTs já emitidos continuam válidos até expirar (padrão 15min, configurável até 60min); não há revogação imediata nesta etapa. Caso seja necessário eliminar também essa janela no cutover, a manutenção precisa cobrir a validade restante a partir do último emissor antigo encerrado, mais margem de relógio, antes de reabrir o tráfego.

Nenhuma configuração Render, segredo, dado de produção/homologação ou infraestrutura foi acessada ou alterada para elaborar este procedimento.
# Atualização F1: origem única

Para a implantação desta etapa, usar o modo de origem única e a transição coordenada descritos em [AUTH_F1_SAME_ORIGIN.md](AUTH_F1_SAME_ORIGIN.md). O Blueprint foi preparado sem aplicar mudanças externas: o serviço Python publica as telas, e o estático antigo vira redirecionamento. Não manter a aplicação antiga fazendo fetch cross-site nem relaxar SameSite. As verificações de banco/versões mistas e rollback operacional abaixo continuam obrigatórias; não há migração nova de F1. Validação publicada pendente.
