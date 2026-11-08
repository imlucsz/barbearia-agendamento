# Objetivo e limites
Corrigir abuso da recuperação de senha e seleção administrativa de barbeiros, preservando autenticação, elegibilidade de agendamento e dados existentes. Sem commit, deploy, e-mails reais ou migrações em homologação/produção.

## Aceite
- Cooldown configurável de 60 segundos por e-mail normalizado, inclusive entre IPs e processos; sem novo token/envio durante a janela.
- Limites adicionais configuráveis: proposta inicial de 5 solicitações aceitas por e-mail/hora e 20 tentativas por IP/hora. Resposta pública genérica para conhecidos, desconhecidos e supressões.
- Reserva atômica persistida antes de enviar; falhas de entrega não desfazem o cooldown nem invalidam links anteriores. Nova tentativa permitida após o cooldown, dentro dos limites adicionais.
- Tokens continuam hash SHA-256, validade de uma hora e uso único. Nenhum segredo em logs/respostas.
- Frontend impede submissões concorrentes e apresenta espera acessível; sem revelar existência da conta.
- Administração lista barbeiros ativos e desbloqueados sem depender de serviços na associação; agendamento preserva elegibilidade específica e falhas de API aparecem ao usuário.

## Áreas e etapas
- [x] Investigar auth.py, rate_limit.py, email.py, request_context.py, modelos e frontend de recuperação.
- [x] Concluir investigação de endpoints/selects administrativos e registrar causa.
- [x] Apresentar proposta de schema antes da implementação (implementação local aprovada em 2026-11-03; migração/deploy remotos não autorizados).
- [x] Criar testes de regressão de recuperação e referências administrativas; verificar falhas antes da correção.
- [x] Adicionar tabela password_reset_limits: chave por escopo + HMAC do identificador, início da janela, contador e próxima permissão; revisão 20261103_01 encadeada a 20261031_01. Nenhuma dependência/infraestrutura nova.
- [x] Implementar reserva por UPSERT condicional PostgreSQL/SQLite. Ordem IP -> e-mail; commit antes de SMTP/Brevo; e-mails inexistentes também limitados. Lease limitada e fencing implementados; testes de reserva abandonada e resultado tardio preservam link novo.
- [x] Substituir o tratamento genérico da rota esqueci-senha no middleware por limites específicos no endpoint, mantendo os demais fluxos inalterados.
- [x] Implementar proteção de submissão/contador e correção administrativa localizada.
- [x] Atualizar README/REQUISITOS_STATUS, executar testes/revisão/Graphify.

## Decisões propostas e alternativas
Usar banco já existente para garantir exclusão entre processos. Limite em memória não protege múltiplos workers; Redis adicionaria infraestrutura sem necessidade. Reaproveitar logs de login/auditoria como reservas misturaria responsabilidades e não oferece chave única por identidade.
Limites por hora usarão janela ancorada na primeira tentativa da identidade, sem promessa de janela móvel; testar a borda. Toda tentativa válida consome orçamento IP, inclusive quando a conta está em cooldown. Chaves HMAC com separação de domínio, mesma normalização do lookup de e-mail e IP canonicalizado; segredo estável entre workers, sem imprimir chave/identificador. Documentar reinício dos buckets em rotação do segredo. Expurgar linhas expiradas em lotes limitados e testar retenção para não acumular e-mails inexistentes indefinidamente.
Persistir reserva antes da entrega impede duplicação mesmo durante envio lento/falha. Em falha, remover apenas o token recém-criado e preservar o anterior; manter a reserva até seu vencimento. Provedor que aceita mensagem e perde resposta não permite garantir entrega exatamente uma vez: não haverá retentativa automática dentro do cooldown.
Não alterar confiança de proxy por suposição: confirmar contrato do edge Render; ignorar X-Forwarded-For arbitrário. O Blueprint usa cf-connecting-ip, validado sintaticamente; proveniência precisa de validação operacional.

## Riscos e recuperação
Migração somente aditiva; não editar revisões existentes, não stamp/drop e não aplicar em dados reais. Limites por IP podem atingir usuários sob NAT; defaults configuráveis. Limites por conta podem atrasar recuperação sob ataque; janela limitada. Falha de banco deve impedir envio. Reversão de código exige revisão de compatibilidade; nunca apagar dados como rollback automático.

## Validação
SQLite temporário obrigatório; PostgreSQL somente banco descartável explicitamente configurado, caso contrário não executado. E-mail mockado. Cobrir primeiro envio, repetição, dez requisições, concorrência com sessões independentes, limite entre IPs, limite IP entre contas, avanço de relógio, falha/timeouts, tokens inválidos/expirados/reusados e login. Paridade Alembic/modelos e preservação de dados. Node para frontend e checks focados; git diff --check. Validação em homologação apenas manual e após autorização separada de migração/deploy.

## Evidências da fase de diagnóstico, anteriores à aprovação
- Estado inicial: nenhum arquivo rastreado modificado; untracked preexistentes preservados.
- auth.py gera e invalida token a cada solicitação; nenhuma reserva por conta ou trava concorrente.
- rate_limit.py conta por IP após execução; não há reserva que impeça múltiplos envios simultâneos.
- auth.js desabilita botão, mas não possui guarda de reentrada/cooldown.
- Proposta de migração ainda não implementada nem aplicada.
- `rtk proxy .\.venv\Scripts\python.exe -m unittest discover -s tests -p test_password_reset.py -q`, em backend, fora do sandbox após bloqueio de acesso ao temporário: 15 testes, 8 aprovados e 7 novos falhando pelos comportamentos ausentes. Concorrência reproduziu 10 envios para 10 solicitações. Nenhum e-mail real.
- `rtk proxy node --test frontend/tests/password-recovery.test.mjs`: 3 falhas esperadas (reentrada, aria-busy e cooldown).
- `rtk proxy node --test frontend/tests/admin-reference-data.test.mjs`: 5 testes, 2 aprovados e 3 falhas esperadas por acoplamento das APIs no Promise.all.
- GET `/users/barbeiros` já lista ativos sem depender de associações; não exclui bloqueados. GET `/services/` público lista serviços. GET `/users/` requer admin. Frontend interrompe todos os selects/formulários se uma referência falhar; requisição específica que falhou em homologação ainda não identificada.
- A suíte Brevo antiga espera rotação imediata de tokens e 429 no quinto pedido, comportamentos que a especificação nova substitui. Adaptar os testes com avanço de relógio e limites explícitos, mantendo cobertura real de invalidação/rollback/uso único.
- Timeouts SMTP/Brevo configuráveis até 120 s podem exceder cooldown de 60 s; a implementação deve tratar envio em andamento/lease e testar relógio sem liberar concorrência indevida. Revisão independente do desenho solicitada.
- Revisão de segurança: timeout pode ocorrer após aceitação pelo provedor; remover o novo token pode resultar em e-mail entregue com link inválido. Preservar link anterior e evitar reenvio automático; registrar e testar a ambiguidade. Operação síncrona também mantém diferença temporal entre contas existentes/inexistentes; uniformidade de corpo/status não garante resistência a análise de tempo. Uma fila durável para equalizar o fluxo seria proposta separada, sem ampliação silenciosa.
- `rtk .venv\Scripts\python.exe -m unittest discover -s tests -p test_barber_service_assignments.py -v`, em backend: 6 testes, 4 aprovados e 2 falhas esperadas. Catálogo retorna bloqueado e criação aceita barbeiro bloqueado associado; correção deve excluir bloqueados do catálogo e da validação centralizada, preservando associação obrigatória.
- Revisão independente concluída, somente leitura. Acrescentar sincronização explícita ao teste concorrente (barreira/envio bloqueado), teste de limite na borda da janela, expurgo e falha fechada do banco. O teste atual usa sessões independentes em threads; não comprova multiprocessos nem PostgreSQL. Cooldown visual começa após a resposta, pois a solicitação fica desabilitada durante todo o envio.

## Execução local aprovada — evidências posteriores

- Implementação usa as mesmas validações existentes de identidade/IP, HMAC com separação de domínio, reservas persistentes, cooldown e limites configuráveis. Não usa create_all em substituição de migrações.
- SQLite completo inicial: 284 testes, OK com 7 skips; Node completo final: 35/35; Playwright desktop/mobile: 6/6 (recuperação, administração e falha isolada de clientes).
- PostgreSQL 18 real descartável: recuperação/migração inicial 22/22, depois 24/24 incluindo conclusão tardia na rota e downgrade concorrente. Quatro processos sincronizados disputam a mesma chave; exatamente uma reserva aceita. Banco/UPSERT não mockados; e-mail mockado. Clusters encerrados e removidos.
- PostgreSQL completo antes do último passe de revisão: 285 testes, OK com 2 skips exclusivos de SQLite. Fechamento final: SQLite 288 executados, 280 aprovados/8 skips PostgreSQL; PostgreSQL 18 real 288 executados, 286 aprovados/2 skips SQLite. Zero falhas finais; clusters encerrados e removidos.
- Ferramenta PostgreSQL: primeiro pg_ctl ficou preso em pipes herdados no Windows; cluster exclusivo encerrado/removido, executor corrigido para arquivo de saída e novas execuções aprovadas. Docker indisponível; usados binários PostgreSQL 18 instalados.
- Revisão independente final (somente leitura) identificou corrida importante no downgrade: inserção poderia confirmar entre SELECT de vazio e DROP. `test_downgrade_prevents_insertion_between_empty_check_and_drop` reproduziu perda de limite em duas conexões reais (RED). Corrigido com lock exclusivo PostgreSQL antes da consulta e BEGIN IMMEDIATE SQLite, mantidos até a conclusão; teste passou no PostgreSQL (GREEN). Downgrade de tabela populada continua recusado sem exclusão de registros.
- Revisão: nenhum achado crítico. Minor diferido/documentado: contador visual continua fixo em 60 s após a resposta; configuração do backend diferente pode divergir da UI, permanecendo a proteção autoritativa no backend. Nenhuma mudança fora do plano.
- Teste adicional `test_late_sender_cannot_invalidate_newer_link_and_login_still_works`: A ultrapassa lease, B conclui, A retorna; somente B permanece utilizável e login com senha redefinida funciona. A lease finita não impõe deadline absoluto ao provedor; risco registrado no runbook.
- Investigação remota de homologação: conector Render respondeu sem workspace selecionado; listado workspace disponível e solicitada confirmação ao usuário, ainda pendente. Não lidos serviços/logs sem identificar o workspace; nenhuma inferência sobre qual chamada falhou na ocorrência concreta.
- Runbook e checklist: [correção de recuperação e barbeiros](../../CORRECAO_RECUPERACAO_E_BARBEIROS_20261103.md).
- Verificação final: `git diff --check` limpo; Graphify AST atualizado para 11497 nós. Não houve commit, push, deploy, migração remota nem envio real. Trabalho local anterior preservado.

## Validação manual futura em homologação
Somente após aprovação e aplicação separada da migração/deploy pelo responsável:
1. Inspecionar Network como administrador em `/auth/me`, `/users/barbeiros`, `/services/` e `/users/`; registrar apenas status/campos não sensíveis, sem copiar Authorization/cookies. Confirmar usuário ativo/desbloqueado sem associação na tela de vínculo.
2. Associar serviço usando conta de teste; confirmar seleção e agendamento elegível. Validar inativo/bloqueado e não associado com massa fictícia controlada. Não alterar Thiago/dados reais como teste automatizado.
3. Simular falha de uma API no navegador e verificar erro local aos campos, preservando referências disponíveis.
4. Em conta/e-mail de teste, pedir recuperação, repetir/cliques rápidos/segunda aba e confirmar no provedor no máximo um envio na janela; não registrar/copiar link ou token.
5. Aguardar cooldown, solicitar novamente e redefinir a senha; validar login com nova senha, rejeição da antiga e do link reutilizado. Validar falha de entrega apenas em transporte de teste.
6. Confirmar no edge a origem confiável do IP, isolamento entre IPs e limitação entre contas; validar múltiplos workers somente com ambiente de teste próprio. Não desabilitar validação ou confiar em headers enviados pelo navegador.
