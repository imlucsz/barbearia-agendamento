# Integração independente de qualidade e acessibilidade

2026-11-04. Branch: feat/qualidade-auth-ux-independente.
Base: a2e849eac2aabe4f03a76232ef7500f9aaf2e7bc. Recomendação: **APTO COM RESSALVAS para PR**.
Sem push, PR, merge, deploy ou acesso a banco real.

## Composição e arquivos por commit

Infraestrutura test-only, administrativos, nomes Unicode, contratos de identidade
e visibilidade acessível. fd4e55a e 800a62c não foram aplicados.

### f1ddd1f — test: isolar testes PostgreSQL e configurações de e-mail

- frontend/e2e/start-test-environment.mjs
- tools/test-recovery-postgres.py

### 20103cf — fix(admin): corrigir seleção e elegibilidade de barbeiros

- backend/app/booking.py
- backend/app/routers/users.py
- backend/tests/test_barber_service_assignments.py
- frontend/assets/js/admin_management.js
- frontend/e2e/essential-flows.spec.mjs
- frontend/tests/admin-reference-data.test.mjs

### 8b26f59 — feat(validation): normalizar nomes Unicode em novas entradas

- backend/app/core/person_name.py
- backend/app/schemas/user.py
- backend/tests/test_person_name.py
- backend/tests/test_person_name_flows.py

### 1fdf985 — test(auth): caracterizar identidade de e-mails sem depender de cooldown

- backend/tests/test_email_identity_contract.py
- backend/tests/test_email_identity_delivery.py
- backend/tests/test_email_identity_postgres.py
- docs/VALIDACAO_IDENTIDADE_EMAIL_20261104.md

### 13c072a — feat(ui): adicionar visibilidade acessível de senhas

- frontend/assets/css/style.css
- frontend/assets/js/password-visibility.mjs
- frontend/e2e/essential-flows.spec.mjs
- frontend/e2e/password-visibility.config.mjs
- frontend/e2e/password-visibility.spec.mjs
- frontend/pages/cadastro.html
- frontend/pages/client-account.html
- frontend/pages/login.html
- frontend/pages/reset.html
- frontend/tests/password-visibility.test.mjs


Este documento, README e status compõem o último commit de documentação.
Os commits e branches originais foram preservados; nenhum histórico reescrito.

## Exclusão da recuperação e adaptações de testes

Diff vazio contra main em backend/app/routers/auth.py, core/security.py,
config.py, models/user.py, core/rate_limit.py, core/email.py,
core/email_identity.py, backend/.env.example, frontend/assets/js/auth.js,
revisões Alembic e testes originais de recuperação/configuração/migração.
Não existem password_reset_limits.py, PasswordResetLimit ou revisão 20261103_01.
O launcher tools/test-recovery-postgres.py é somente infraestrutura de teste.

Duas funções de e-mail pressupunham supressão por cooldown. Agora verificam
identidade/destinatário como primeira solicitação em fixtures independentes,
mantendo resposta genérica, um envio conhecido, destinatário canônico,
vínculo ao usuário/token e flag de uso. Casos independentes usam IPs fictícios
próprios, sem alterar/mockar limites do runtime. Não se adotou uma política
de envios duplicados. As oito regressões originais de recuperação continuam.

## Validação nova

| Execução | Resultado |
|---|---|
| full-sqlite | Ran 302 tests in 279.179s; OK (skipped=12); 282.486 s |
| full-postgres | Ran 302 tests in 267.737s; OK (skipped=2); 304.551 s |
| full-node | # tests 34; # pass 34; # fail 0; # skipped 0; 0.584 s |
| full-essential | 1 failed; 55 passed (3.0m); 181.387 s |
| essential-denied-repeat | 6 passed (23.6s); 24.973 s |
| full-essential-second | 56 passed (2.5m); 151.852 s |
| visibility-e2e | 32 passed (1.0m); 62.22 s |

SQLite: 302 executados, 290 aprovados e 12 casos PostgreSQL ignorados.
PostgreSQL: 302 executados, 300 aprovados e 2 casos SQLite ignorados.
Não são casos únicos somáveis. PostgreSQL 18.6 real, cluster novo somente
loopback/banco *_test, UTF8 e locale C; inclui cadastro concorrente real,
índice funcional e collation. Cluster encerrado/removido. Revisões existentes
somente em bancos descartáveis; nenhuma revisão nova ou banco real.

Node: 34 aprovados. Visibilidade: 32 cenários em Chromium desktop/320 px,
Firefox e WebKit. Essenciais: desktop1280x800/mobile390x844.
Trace/screenshot/vídeo da validação essencial desativados em config ignorado,
sem mudar o versionado. Nenhuma dependência instalada; ambientes existentes
reutilizados, inclusive junction node_modules.

### Instabilidade E2E preservada

Primeira rodada completa: 55/56; timeout mobile no caso de usuário comum
negado na tela administrativa. A chamada direta recebeu 403; o timeout
ocorreu esperando resposta da agenda durante redirecionamento. Seis repetições
isoladas e segunda rodada completa passaram, sem mudar código ou asserções.

Revisão somente leitura confirmou corrida preexistente: agenda_admin.js
consulta a agenda enquanto admin_management.js consulta /auth/me e redireciona
o cliente; a navegação pode cancelar a consulta antes do evento response.
Teste e trechos relevantes são iguais a main. Não se interpretou isso como
acesso indevido nem se ocultou a falha inicial. Nenhuma correção desse caso
foi incorporada.

## Reprodução e checks

- Python existente, cwd backend: -m unittest discover -s tests -q.
- Python existente, cwd raiz: tools/test-recovery-postgres.py discover -s tests -q.
- Node: node --test frontend/tests/*.test.mjs.
- Essenciais: node node_modules/@playwright/test/cli.js test --config=test-results/independent-essentials.config.mjs.
- Visibilidade: mesmo CLI com --config=frontend/e2e/password-visibility.config.mjs.
- git diff --check main...HEAD; git diff --cached --check.

O config essencial ignorado importa o config versionado, seleciona seus
dois projetos essenciais e desativa captura. O setup limpa SMTP/Brevo herdado
e usa SQLite temporário. Não executar esses testes contra banco real.

Revisão independente: nenhum defeito concreto nos pacotes incluídos.
Sintaxe de 19 arquivos Python/JS alterados aprovada; padrões de credenciais
reais não encontrados. Fixtures são fictícias. Manifests/locks inalterados.
Índice/check conferidos antes de cada commit. Graphify atualizado AST no
worktree novo; saída ignorada, sem incluir Graphify, skills, pessoal ou artefatos.

## Ressalvas e validação antes de publicação

- Recuperação permanece exatamente como main, incluindo riscos temporais
  e ausência do cooldown excluído; não foi corrigida por esta branch.
- E-mail legado/Unicode/collation continua caracterizado; sem correção de
  dados/política e sem prova de entrega real.
- Sem validação Render, banco real, aparelhos físicos ou versão PostgreSQL
  efetivamente contratada (Blueprint declara16, ensaio usou18.6).
- Instabilidade E2E acima preservada; sua correção requer escopo próprio.
- Rever base/título/descrição por esta composição e autorização antes de
  publicar. Nenhuma migração real a aplicar nesta integração.
- Lote4, sessões, recuperação e investigação arquitetural fora do escopo.
