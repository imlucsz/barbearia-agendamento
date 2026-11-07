# Etapa 2: sessões e limitação de autenticação

## Objetivo e limites
Base d4850cd9, branch fix/auth-security-stage2-sessions, worktree próprio. PR30 e demais worktrees intocados. Sem commit/publicação, dependências novas, produção ou dados reais.

## Reproduções
- [x] Conta própria neutraliza histórico de falhas de outra conta: assertiva esperava429, recebeu401.
- [x] Três verificações de senha admitidas antes de persistir resultados, com limite2. Eventos controlados, sessões independentes, sem carga.
- [x] Refresh confirma T2, resposta fica pausada; logout com T1 retorna200; resposta tardia entregaT2 e ele ainda renova com200, quando deveria401.
- [x] Caracterização de access JWT: continua aceito após logout e é rejeitado após expiração controlada. Esse comportamento não foi tratado como bypass de assinatura ou falha de expiração.

## Autorização e implementação
A investigação parou na barreira de migração; o usuário posteriormente autorizou explicitamente a migração aditiva e as correções somente neste worktree. A PR30 permanece intacta.

Implementado: revisão 20261107_01 após 20261031_01, com account_key HMAC de identidade normalizada, em_andamento default false, expira_em e índice conta/rota/tempo. Campos nulos preservam histórico legado. Upgrade e paridade passaram em SQLite, com histórico preservado; downgrade é recusado antes de DDL destrutivo seguindo política forward-only existente. Nenhum stamp, drop, revisão histórica alterada ou create_all em produção.
Reservas são admitidas atomicamente antes da senha: PG advisory locks ordenados e READ COMMITTED explícito; SQLite BEGIN IMMEDIATE. Falhas por conta 5/60s, IP 30/300s, frequência IP 60/60s, concorrência2/conta e4/IP, lease 120s; variáveis LOGIN_RATE_* documentadas no README. Tentativas bloqueadas não prolongam janelas; reservas abandonadas contam como falha nas janelas originais e deixam de ocupar concorrência após expirar. A transação termina antes da senha; sem reset cruzado ou Redis. Lease não garante teto de CPU se requisições ultrapassarem 120s.

Alternativa sem migração: buckets técnicos em campos existentes de login_attempts, com locks de admissão. Requer decidir explicitamente a nova semântica de ip/rota e a representação de reservas; não implementar silenciosamente. Contador apenas em memória não substitui estado compartilhado.

## Sessões e decisão sobre access token
Implementado B: logout revoga família identificada por T1 mesmo rotacionado. Refresh adquire lock de User e relê o token depois de esperar; logout, revogação por reset/bloqueio e replay seguem ordem User → RefreshToken. PG SELECT User.id FOR UPDATE não repopula User com senha dirty do reset; SQLite usa UPDATE sem alterar hash ou estado ORM. Famílias independentes permanecem válidas. Nenhuma nova tabela de sessões.
Cookie tardio pode reaparecer no navegador; o servidor deve rejeitá-lo mesmo assim. Não relaxar HttpOnly/Secure/SameSite/Origin. Avaliar guarda no cliente para ignorar refresh concluído depois de logout somente após demonstrar necessidade; nenhum frontend alterado.

Decisão C: manter access token curto (padrão15min, máximo configurável60min), sem blacklist nem consulta adicional por requisição. O resolvedor existente já verifica conta ativa/bloqueada. Logout/reset revogam renovação, não JWT já emitido; risco residual é sua validade restante, inclusive por resposta atrasada. Revogação imediata por sessão exigiria desenho separado. Caracterizações cobrem validade residual e expiração após logout e reset.

## Infraestrutura e pendências
Blueprint declara CLIENT_IP_SOURCE=cf-connecting-ip. Código exige um IP válido nesse header e ignora X-Forwarded-For; modo direct ignora encaminhados. Isso não comprova que a origem publicada não pode ser acessada contornando o edge. Infraestrutura real não consultada nem testada; não declarar confiança validada.
PostgreSQL descartável não configurado. Reprodução concorrente somente SQLite; sem validação PostgreSQL, navegador/cookies reais ou Render.

## Evidência
Na investigação, 4 testes geraram 3 falhas de segurança e 1 caracterização aprovada. Após correções, os 4 passaram e a cobertura foi ampliada para 8. Rate limiting: 13 aprovados; migração: 7 aprovados e 1 PG ignorado; Node: 51 aprovados. Suíte completa final: 336 testes, 324 aprovados e 12 ignorados, sem falhas (327,650s). Revisão independente sem achados de produção. Um teste de sincronização foi corrigido para ContextVar porque FastAPI também executa logout em worker; a execução completa anterior teve essa falha e a final passou. Preservação de histórico e recusa de downgrade destrutivo testadas. Graphify AST atualizado no worktree. Nenhum segredo impresso, commit ou publicação.

## Revisão de concorrência e implantação — continuação autorizada

Plano curto: corrigir a inversão comprovada de ordem SQL antes de ampliar a arquitetura de reservas. Não há autorização para infraestrutura, outra migração ou publicação. O resultado de 324 Python/51 Node acima pertence ao estado anterior a esta revisão.

- [x] Preservar estado inicial e consultar grafo somente no worktree da etapa 2.
- [x] Acrescentar `test_auth_stage2_concurrency.py`: expiração com hash ativo, ordem User antes do consumo do token, token inválido sem lock e interleaving reset/exclusão exclusivo PostgreSQL. Antes da correção: duas falhas, um aprovado e um ignorado (PostgreSQL indisponível).
- [x] Em `routers/auth.py`, adquirir User antes do UPDATE condicional de PasswordResetToken, mantendo consumo único, rollback e revogação transacionais. Recalcular `now` após esperar; o teste temporal foi primeiro reproduzido com 200 em vez de 400 e agora passa. Nenhuma alteração de schema.
- [x] Executar regressões de autenticação, reset, sessões e exclusão: fechamento selecionado de 83 testes, 80 aprovados, 1 falha A, 2 ignorados PG, 0 erros (83,237s). Node 51 aprovados. PostgreSQL não configurado; não declarar validação concorrente nesse banco.
- [x] Documentar troca sem workers antigos em `docs/security/AUTH_STAGE2_ROLLOUT.md`; `render.yaml` e infraestrutura inalterados. Startup existente testado localmente em SQLite. Roteiro inclui revogação histórica sujeita a autorização separada, cookies tardios e access JWT residual.
- [x] Registrar resultados atuais, revisar diff e preservar Graphify local sem atualização por instrução explícita desta tarefa. Revisão independente B/C concluída e recomendação temporal aplicada. Sem commit.

Bloqueio A: uma lease renovável não comprova término do hash após suspensão/partição, e cancelar HTTP não cancela uma thread nativa. A alternativa localizada de reserva sem expiração pode prender conta/IP após crash, contrariando recuperação automática. Locks mantidos consomem conexões e sua perda não encerra o hash. Teto estrito junto com recuperação automática exige um desenho de execução supervisionada e encerramento confirmado antes de liberar capacidade; apresentar alternativas e obter autorização antes dessa mudança. O teste de expiração fica falhando visivelmente, sem expectedFailure/skip, até resolver o bloqueio; não declarar a etapa pronta nem os testes todos aprovados.

## Decisão posterior autorizada: capacidade local pragmática

O usuário aprovou limite estrito por processo, inicialmente um, mantendo a admissão distribuída. Não aprovou subprocessos, coordenador global, outra migração ou infraestrutura. O bloqueio arquitetural descrito acima é substituído por esta garantia mais estreita: teto agregado depende da quantidade real de processos vivos, inclusive em troca de versão.

- [x] Testes primeiro: seis testes iniciais falharam antes da correção e passaram depois; cobertura ampliada para capacidade compartilhada, threads, configuração, upgrade completo, falhas, timeout do aguardante, cancelamento HTTP com trabalho ainda ativo, expiração e invalidação antes da sessão.
- [x] `core/security.py`: semáforo limitado por processo, `AUTH_PASSWORD_MAX_CONCURRENCY=1` validado na inicialização; aquisição não bloqueante e liberação no finally da chamada síncrona, sem mudar parâmetros criptográficos. Hash ausente também participa da decisão de capacidade, sem verificar senha, para manter resposta de saturação uniforme.
- [x] `core/login_rate_limit.py`: associar ID e sinal de cancelamento à requisição; consumir reserva em andamento e não expirada na transação da sessão. Cancelamento observado antes da autorização invalida a tentativa. Nada de locks de banco durante o hash.
- [x] `routers/auth.py`: manter CAS User; consumir reserva após adquirir User e antes de criar tokens. Falha desfaz também eventual upgrade. O consumo condicional é o ponto de autorização; cancelamento pode concorrer entre última checagem e commit e não equivale a revogação retroativa de transação autorizada.
- [x] Validação: 350 Python, 336 aprovados/14 ignorados, sem falhas (266,586s); Node51 aprovados. PostgreSQL não configurado: testes concorrentes entre processos e migrações PG não executados. Revisão independente sem bypass da capacidade ou nova inversão de locks; janela de cancelamento/commit explicitada e timeout da barreira PG corrigido.
- [x] README/status/roteiro atualizados, diff/check revisado; PR30 e Graphify preservados. Sem staging/commit/publicação, schema/dependências/infraestrutura novos.

## Classificação explícita — revisão 20261107_02 autorizada

- [x] Regressões primeiro: 5/30 respostas de saturação não esgotam falhas, 60 continuam esgotando frequência; resultado real após exceção; término idempotente, concorrência, cancelamento e expiração. Cenários principais reproduzidos antes da correção; 14 testes novos aprovados.
- [x] Nova migração aditiva 20261107_02 após 20261107_01 e colunas nullable `resultado`/`motivo_finalizacao`; sem alterações em revisões anteriores, dados ou índices existentes. Sem índice novo: leituras já delimitadas pelos índices de conta/IP/rota/tempo.
- [x] Estados novos: pendente, sucesso, credencial_rejeitada, neutro. Motivos são códigos internos fechados, nunca texto de exceções ou dados de credenciais. `sucesso=True` apenas para sessão confirmada; neutros preservam False, sem participar de falhas. Registros antigos com resultado NULL mantêm a interpretação binária conservadora nas janelas originais, inclusive reservas legadas; pendentes novos expirados sem veredicto não viram rejeição de senha. Sem backfill que invente resultados históricos.
- [x] Capturar decisão de credenciais na rota, antes de auditoria/commit, sem inferir por status HTTP. Credencial realmente rejeitada continua rejeitada se ocorrer erro/interrupção/expiração posteriores; 503 sem rejeição conhecida é neutro. Nenhuma contagem duplicada. Sucesso registrado dentro da transação de sessão; rollback permite finalização neutra posterior.
- [x] UPDATE de finalização somente onde resultado=pendente; expiração/invalidação sem rejeição conhecida vira neutro. Claim exige pendente e reserva viva. Reservas vivas continuam consumindo provisoriamente orçamento de admissão; frequência conta todos os registros. Rejeição por limite acontece antes de criar reserva e não é falha de credencial.
- [x] Validação: seleção49 com47 aprovados/2 ignorados; suíte completa365 com351 aprovados/14 ignorados, sem falhas (246,153s); Node51 aprovados. Após guarda explícita de pendência, testes de outcomes14 reexecutados e aprovados. Upgrade/histórico/índices/paridade SQLite aprovados. Revisão independente concluída, com prioridades de legado e rejeição conhecida corrigidas por testes red/green. PostgreSQL não configurado/não executado.
- [x] README/roteiro/status atualizados; diff/check revisado. Sem staging/commit/publicação; PR30, Graphify e demais worktrees preservados.
