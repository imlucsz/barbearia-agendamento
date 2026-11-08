# Recuperação de senha e seleção administrativa — alteração local

## Diagnóstico e correções

A recuperação gerava outro token e invalidava os anteriores em cada pedido; o limite por IP era verificado antes e registrado depois da operação. Testes reproduziram dez tentativas concorrentes de envio. A nova admissão usa `password_reset_limits`, com chave HMAC por escopo/e-mail normalizado/IP validado, UPSERT condicional e commit antes de enviar. Não há trava em memória nem dependência nova. As mesmas regras são aplicadas a e-mails inexistentes, sem persistir e-mail/IP em claro nessa tabela.

Padrões configuráveis: cooldown 60 s, 5 reservas por conta e 20 tentativas por IP a cada 3600 s. A janela é ancorada na primeira tentativa da identidade, não é uma janela móvel. Cada tentativa válida consome orçamento de IP, mesmo se o e-mail já estiver limitado. Limites e supressões retornam o mesmo HTTP 200/corpo genérico que contas desconhecidas e falhas de entrega; a rota deixa de usar o antigo 429 no quinto pedido. Login e demais rotas mantêm seu limiter anterior.

Uma reserva de envio impede novo envio durante I/O lento. Seu prazo é o maior entre o cooldown e `8 × timeout do transporte + 60 s` (padrão 140 s); não se trata de um deadline absoluto do SMTP. Reserva abandonada expira; identificador de reserva impede conclusão tardia de invalidar links mais novos. Falha de entrega remove apenas o token novo, conserva o link anterior e não desfaz cooldown/contadores. Sucesso invalida tokens anteriores; tokens continuam SHA-256, uma hora de validade, consumo atômico de uso único e revogação de sessões na redefinição. Registros de limite inativos há mais de duas janelas são expurgados em lotes de até 100 durante solicitações admitidas.

No frontend, a recuperação bloqueia reentrada do handler e marca o formulário com `aria-busy`. Após a resposta, mantém o botão desabilitado por 60 s com contador; inclusive em erro de rede, pois o servidor pode já ter aceitado o pedido. O feedback permanece genérico. Recarregar a página não remove o controle no servidor.

O catálogo `/users/barbeiros` já incluía ativos sem associação; foram excluídos os bloqueados. A validação central de agendamento agora também rejeita bloqueados, mantendo exigência de associação e regras de horário/jornada/bloqueio. No painel, serviços, barbeiros e clientes são tratados independentemente após `Promise.allSettled`; a falha de uma consulta deixa mensagem específica e desabilita apenas os selects afetados. Erros 401 continuam sendo erros de autenticação.

## Migração e reversibilidade

Revisão **20261103_01**, anterior **20261031_01**, arquivo `backend/alembic/versions/20261103_01_password_reset_limits.py`. Somente cria a tabela de controles e um índice; não altera usuários, serviços ou tokens existentes. Upgrade não usa `create_all()`.

Downgrade para `20261031_01` é suportado quando a tabela nova está vazia. A verificação e o DROP ficam sob bloqueio exclusivo no PostgreSQL (timeout de aquisição 5 s) ou transação de escrita SQLite. Se houver registros, recusa a operação antes de apagar qualquer coisa, preservando limites ativos; inserts concorrentes não conseguem confirmar no intervalo. Não apague controles para forçar rollback; deixe a tabela aditiva instalada ao reverter código e planeje a recuperação com o responsável.

## Evidências e comandos

- `rtk proxy node --test frontend/tests/*.test.mjs`: 35 aprovados.
- Em `backend`: `rtk proxy .\.venv\Scripts\python.exe -m unittest discover -s tests -q`: primeira suíte completa 284 executados, 277 aprovados, 7 ignorados por exigirem PostgreSQL. Teste adicional de configuração incluído depois; validação final registrada no plano/status.
- `rtk proxy backend\.venv\Scripts\python.exe tools/test-recovery-postgres.py discover -s tests -p test_password_reset*.py -q`: PostgreSQL 18 real, 22 aprovados, incluindo concorrência entre quatro processos com barreira, sessões independentes, envio lento, lease abandonada, fencing, upgrade/downgrade e paridade dos modelos. Nenhum mock de banco/UPSERT. Transporte de e-mail mockado. Cluster criado em loopback, encerrado e removido.
- `rtk proxy npx --no-install playwright test --config frontend/e2e/playwright.config.mjs --project desktop-1280x800 --project mobile-390x844 --grep 'recupera|painel administrativo|referência de clientes'`: 6 aprovados. Banco temporário criado por Alembic; SMTP/Brevo desabilitados.
- Primeira tentativa do executor PostgreSQL: falha de timeout causada por pipes herdados pelo daemon no Windows. Executor corrigido para usar arquivo; cluster anterior encerrado/removido. Essa falha de ferramenta não foi tratada como aprovação dos testes.
- Revisão independente identificou uma corrida no downgrade, reproduzida como falha em teste com duas conexões PostgreSQL reais. Após o bloqueio exclusivo, todos os 24 testes focados de recuperação/migração passaram, incluindo chegada tardia de um envio antigo sem invalidar o novo link e login após redefinição.
- Suíte SQLite final: 288 executados, 280 aprovados, 8 ignorados exclusivamente por backend PostgreSQL (identidade de e-mail, bootstrap PostgreSQL, quatro testes de migração legada, paridade PostgreSQL e concorrência DDL PostgreSQL). Nenhuma falha. No PostgreSQL, dois testes de bootstrap exclusivos de SQLite são ignorados.
- Suíte PostgreSQL 18 final: `rtk proxy backend\.venv\Scripts\python.exe tools/test-recovery-postgres.py` — 288 executados em 219,660 s, 286 aprovados, 2 ignorados exclusivos de SQLite, zero falhas. Cluster encerrado e removido. Inclui concorrência real entre quatro processos e corrida de downgrade entre duas conexões; somente o transporte de e-mail usa mocks.
- Revisão independente concluída e achado importante corrigido por RED→GREEN; minor visual documentado. `git diff --check` limpo e Graphify AST atualizado. Nenhuma falha final pendente; publicação e verificação da ocorrência em homologação não foram concluídas nem presumidas.

## Arquivos alterados nesta tarefa

| Área | Arquivos |
| --- | --- |
| Recuperação/backend | `backend/app/core/password_reset_limits.py` (novo), `backend/app/routers/auth.py`, `backend/app/core/rate_limit.py`, `backend/app/models/user.py`, `backend/app/config.py` |
| Barbeiros/backend | `backend/app/routers/users.py`, `backend/app/booking.py` |
| Schema | `backend/alembic/versions/20261103_01_password_reset_limits.py` (novo) |
| Frontend | `frontend/assets/js/auth.js`, `frontend/assets/js/admin_management.js` |
| Testes Python | `backend/tests/test_password_reset.py`, `test_barber_service_assignments.py`, `test_brevo_email.py`, `test_configuration.py`, `test_schema_migrations.py`, `test_password_reset_limits_migration.py` (novo), `password_reset_process_worker.py` (novo) |
| Testes frontend | `frontend/tests/password-recovery.test.mjs` e `admin-reference-data.test.mjs` (novos), `frontend/e2e/essential-flows.spec.mjs`, `frontend/e2e/start-test-environment.mjs` |
| Executor isolado | `tools/test-recovery-postgres.py` (novo) |
| Documentação/configuração exemplo | `README.md`, `backend/.env.example`, `docs/REQUISITOS_STATUS.md`, este runbook e `docs/superpowers/plans/2026-11-03-recuperacao-e-barbeiros.md` |

`graphify update .` atualizou o grafo AST local; arquivos não rastreados preexistentes foram preservados. Nenhuma revisão Alembic anterior foi editada.

## Riscos e investigação pendente

- Sem evidência dos logs/Network da ocorrência não é possível nomear qual chamada de homologação falhou. Consultas relevantes: `GET /auth/me`, `/services/`, `/users/barbeiros` e `/users/`. Não presumir que o frontend resolva falhas de autorização, publicação, CORS ou indisponibilidade. A investigação por Render está pendente da confirmação do workspace exigida pelo conector.
- `CLIENT_IP_SOURCE=cf-connecting-ip` depende de edge confiável e de não aceitar acesso direto com cabeçalho falsificado. Não habilitar confiança em `X-Forwarded-For` arbitrário. Confirmar operacionalmente a proveniência do IP; não foi alterada a infraestrutura.
- Status/corpo genéricos não eliminam diferença temporal do envio síncrono entre e-mails existentes/inexistentes. Não foi introduzida fila ou infraestrutura não aprovada.
- SMTP/Brevo pode aceitar a mensagem e perder a resposta. Não há garantia de entrega exatamente uma vez: em falha o link novo pode ser removido mesmo se a mensagem chegar, mas o link anterior é preservado. Não há reenvio automático. Uma operação excepcionalmente longa além do prazo da reserva pode se sobrepor a nova tentativa; fencing protege a conclusão tardia. Mudanças de prazo exigem considerar timeout/latência do provedor.
- O HMAC usa `SECRET_KEY` com separação de domínio. A chave deve ser igual entre workers; sua rotação reinicia efetivamente os buckets. NAT pode compartilhar orçamento IP. A proteção por conta evita contornar cooldown apenas trocando IP.
- O contador visual é fixo em 60 s após a resposta; se o cooldown configurado no backend mudar, pode divergir da interface. Trata-se de minor documentado da revisão, sem enfraquecer o limite obrigatório do servidor.
- Limpeza é oportunista e limitada, não um agendamento novo; sob tráfego distribuído extremo ainda é necessário monitorar volume da tabela e proteção do edge.

## Procedimento futuro de migração em homologação — não executado

1. Obter autorização separada para migração/deploy. Confirmar serviço, instalação e banco de destino sem copiar connection strings ou credenciais para chat/logs.
2. Confirmar backup e ensaio de restauração; combinar janela de manutenção e responsável. O launcher Render existente executa `upgrade head` em cada início: não reiniciar/publicar a versão nova sem aprovação de migração.
3. Com o ambiente seguro já configurado e na pasta `backend`, executar `python -m alembic current` e `python -m alembic heads`. Conferir revisão atual `20261031_01` e alvo `20261103_01`; investigar qualquer divergência antes de continuar.
4. Somente com autorização de execução no destino correto: `python -m alembic upgrade 20261103_01`. Não usar `stamp`, `create_all()`, reset/clean ou exclusão de dados.
5. Conferir `python -m alembic current`, schema e paridade esperados; publicar/reiniciar somente após aprovação separada e verificar `/ready`. A versão antiga exige seu head exato; planejar a troca para não prometer zero downtime.
6. Se falhar, interromper publicação e analisar diagnóstico sanitizado. Não executar downgrade automático nem apagar limites/dados. O código anterior não oferece a nova proteção de recuperação.

## Checklist antes de qualquer deploy

- [ ] Aprovação explícita de migração e deploy, destino e backup/restauração confirmados.
- [ ] Suítes SQLite, PostgreSQL real e Node aprovadas no estado final; revisão independente concluída; `git diff --check` limpo.
- [ ] Status da requisição original em homologação identificado ou pendência formalmente mantida.
- [ ] IP confiável no edge, mesmos parâmetros/HMAC entre workers, limites adequados para NAT e timeouts verificados.
- [ ] Conta fictícia/controlada e caixa de teste preparadas; sem registrar links, tokens, cookies ou Authorization.
- [ ] Administrador vê ativo/desbloqueado sem vínculo; vincula serviço; agendamento rejeita sem vínculo/inativo/bloqueado. Falha isolada de clientes não esvazia barbeiros/serviços.
- [ ] Recuperação: primeiro envio, repetição, concorrência, IPs diferentes, cooldown, limite de IP/conta e falha de transporte verificados em ambiente de teste.
- [ ] Redefinição/login, token inválido/expirado/reutilizado e revogação de sessão verificados.
- [ ] `/ready`, erros HTTP e volume de envio/limites monitorados depois da mudança aprovada.

Nenhum commit, push, deploy, e-mail real ou migração em homologação/produção foi realizado nesta tarefa.
