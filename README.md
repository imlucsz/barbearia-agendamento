# Sistema de Agendamento Online para Barbearia



Aplicação web para uma barbearia por instalação: apresentação pública dos serviços, reserva de horários pelo cliente e gestão da agenda pela equipe. Cada instalação possui configuração e banco próprios; o sistema não implementa multi-tenancy.

**Status:** versão candidata em homologação. Recursos implementados e resultados locais não equivalem a prontidão de produção; confira [requisitos e evidências](docs/REQUISITOS_STATUS.md), [rastreabilidade](docs/RASTREABILIDADE.md) e [checklist operacional](docs/CHECKLIST_PRODUCAO.md).

Projeto acadêmico do curso de Desenvolvimento de Software Multiplataforma (DSM) da FATEC Itaquera. O sistema reúne um site público, fluxo de agendamento para clientes e painel de gestão da barbearia.

## Funcionalidades e perfis

| Perfil | Recursos |
| --- | --- |
| Visitante | Catálogo com preço/duração/descrição, contatos, mapa, informações da instalação e avaliações públicas. |
| Cliente | Cadastro, login, recuperação de senha, escolha de serviço/profissional/data/horário, confirmação, histórico, cancelamento, reagendamento e avaliação de atendimento concluído. Conta com exportação JSON/PDF e solicitação autenticada de anonimização. |
| Barbeiro | Própria agenda, registro de atendimento, agendamento avulso e gestão das próprias jornadas/bloqueios, conforme autorização da API. |
| Administrador | Agenda da equipe, serviços e vínculos com profissionais, jornadas/bloqueios, clientes, informações institucionais, moderação, relatórios e consulta de auditoria. |

O fluxo de reserva segue **serviço → profissional → data e horário → confirmação**. A API verifica jornada, bloqueios, conflitos e duração; a janela de reserva é de até 14 dias. Cancelamento/reagendamento pelo cliente exigem 24 horas de antecedência, com até dois reagendamentos. Preço e duração ficam registrados no agendamento.

## Arquitetura e tecnologias

- **Frontend:** HTML5, CSS3 responsivo e JavaScript ES Modules (Vanilla).
- **Backend:** Python, FastAPI, Pydantic e SQLAlchemy.
- **Banco de dados:** SQLite em desenvolvimento/testes; PostgreSQL em produção, com evolução do schema por Alembic.
- **Autenticação:** JWT Bearer (PyJWT); senhas novas com Argon2id e verificação compatível com hashes bcrypt existentes.
- **Apresentação:** GSAP local na HOME, vídeo WebM local no Ritual e Three.js na Estrelinha opcional. O import map da Estrelinha ainda usa CDN; a apresentação principal e os dados do negócio têm módulos independentes.

O navegador consome a API HTTP; não há acesso direto do frontend ao banco. `home.js` mantém catálogo, autenticação, contatos e avaliações; `home-experience.mjs` controla apresentação. Personalização por instalação usa `installation-config.mjs`, tokens CSS e configuração do backend.

## Experiência da página inicial

A HOME combina intro pulável, hero editorial, conteúdo comercial e CTA de agendamento. O Ritual apresenta PREPARO → TÉCNICA → ACABAMENTO em vídeo conduzido pelo scroll, com scrub contínuo e reversível em todas as larguras/alturas. Desktop usa pin; viewports compactas usam palco sticky e composição própria. `prefers-reduced-motion: reduce` mantém poster e os três capítulos legíveis, sem scrub obrigatório. Falha de mídia também preserva a narrativa estática.

A Estrelinha é uma assinatura visual opcional, com até três aparições breves e decorativas; não é chatbot. A flag `features.estrelinhaWidget` controla sua presença. Detalhes em [integração HOME](docs/HOME_MOTION_INTEGRATION.md), [decisões de produto](specs/home-experience.md) e [Estrelinha](docs/ESTRELINHA_CINEMATICA.md).

Chrome e Edge tiveram scrub validado nas viewports registradas no relatório. Firefox falha ao criar páginas neste ambiente, e WebKit Windows rejeita o mesmo asset em um vídeo isolado. Isso não demonstra compatibilidade total com Firefox/Safari ou aparelhos físicos. Não há fallback específico por navegador.

O [Motion Lab](frontend/e2e/motion-lab/README.md) permanece como laboratório separado, com estudos de espelho/vídeo e SVG/Three que originaram a integração. Não integra o build público. Suas comparações com `/reference` dependem de um HTML externo de referência, que não faz parte do produto nem é necessário à HOME.

## Implantação por instalação

Para preparar uma barbearia com domínio, banco e configuração próprios, consulte [Implantação e reutilização](docs/IMPLANTACAO_E_REUTILIZACAO.md). O procedimento não copia dados de clientes nem configura multi-tenancy. O [inventário LGPD](docs/LGPD.md) descreve exportação, exclusão e retenção implementadas; revise as bases legais com assessoria jurídica.

Para criar um checkout limpo por barbearia, mapear personalizações e aplicar atualizações do núcleo, siga o [guia de reutilização e atualização](docs/REUTILIZACAO_E_ATUALIZACAO.md) e use os scripts em `tools/new-installation/`.

## Requisitos

- Python compatível com as dependências do backend; a versão de referência está em [`backend/.python-version`](backend/.python-version).
- Node.js 22 e npm para build estático e testes frontend; versão em [`frontend/.node-version`](frontend/.node-version).
- Navegador moderno.
- Git, para clonar o repositório.
- Opcional: PostgreSQL instalado e seu driver Python, caso não use SQLite.

O frontend usa ES Modules nativos sem transpilação; veja [compatibilidade de navegadores](docs/COMPATIBILIDADE.md). O GitHub Actions executa testes Python, Node, auditorias de dependências e Playwright; confira `.github/workflows/ci.yml`.

Para backup diário criptografado, teste trimestral de restauração e recuperação de desastres, consulte [o plano operacional](docs/PLANO_RECUPERACAO_DESASTRES.md). A instalação e o armazenamento externo são configurados pelo operador.

Para consultar o andamento dos requisitos, veja a [auditoria de implementação](docs/REQUISITOS_STATUS.md) e a [matriz de rastreabilidade entre requisitos, código, rotas e testes](docs/RASTREABILIDADE.md). Antes da publicação, use também o [checklist de prontidão para produção](docs/CHECKLIST_PRODUCAO.md). A matriz identifica lacunas que ainda dependem de infraestrutura externa ou validação adicional.

## Executar localmente

Abra um terminal na raiz do repositório.

### 1. Configurar e iniciar o backend

No PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Antes de iniciar, edite `backend/.env`: mantenha `APP_ENV=development`, configure uma `SECRET_KEY` privada e persistente (sem valor padrão) e confira banco/origem do frontend. Copie `.env.example` somente na primeira configuração; preserve um `.env` existente. Depois aplique as migrações e inicie a API:

```powershell
python -m alembic upgrade head
uvicorn app.main:app --reload
```

Esses comandos de instalação alteram o banco configurado; use somente o banco local intencionalmente escolhido. Não execute migrações de demonstração contra dados reais.

No macOS/Linux, a ativação do ambiente virtual é:

```bash
source .venv/bin/activate
```

A API fica em `http://127.0.0.1:8000`. A documentação interativa do FastAPI fica em `http://127.0.0.1:8000/docs`; o schema OpenAPI está em `/openapi.json`.

No ambiente local (`APP_ENV=development`), o banco padrão é `sqlite:///./barbearia.db`, relativo ao diretório `backend`. Nos demais ambientes, `DATABASE_URL` deve ser configurada explicitamente; a API falha ao iniciar se estiver ausente. A aplicação não cria nem altera tabelas no startup: aplique as migrações Alembic antes de iniciar a API. Se a revisão instalada não for a atual, o startup registra um aviso sem incluir a URL do banco.

### Migrações de banco com Alembic

O Alembic usa a mesma variável `DATABASE_URL` da aplicação, carregada do ambiente ou de `backend/.env`. Nenhuma URL com credenciais fica gravada no repositório. Execute os comandos a partir de `backend`, com as dependências do `requirements.txt` instaladas:

```powershell
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic history
.\.venv\Scripts\python.exe -m alembic upgrade head
```

`20261027_01` preserva a evolução histórica que remove a restrição antiga de `appointments(service_id, data_hora)`. A revisão `20261028_01` cria as nove tabelas do schema inicial; `20261029_01` adiciona consentimentos LGPD versionados e refresh tokens rotativos; `20261029_02` acrescenta tentativas de login; `20261029_03` acrescenta auditoria; `20261029_04` permite desvincular consentimentos e sessões revogadas durante anonimização; `20261029_05` adiciona a descrição pública dos serviços; `20261029_06` adiciona índices de disponibilidade; `20261031_01` normaliza identidade de e-mail por trim/lowercase e recusa conflitos sem unir contas. O schema atual tem treze tabelas. Em banco existente, a adoção só reconhece schemas suportados e falha sem apagar tabelas ou registros. Não há `stamp` automático.

Procedimento de adoção:

- **Banco novo PostgreSQL ou SQLite:** configure `DATABASE_URL` para o banco vazio exclusivo desta instalação e execute `python -m alembic upgrade head` antes de iniciar a API. A revisão `20261028_01` cria o schema legado de nove tabelas; as revisões posteriores completam as treze tabelas e os controles atuais.
- **Banco local de desenvolvimento SQLite existente:** pare a API e, no diretório `backend`, faça backup e prepare um novo arquivo sem apagar o antigo:

  ```powershell
  Copy-Item .\barbearia.db .\barbearia.pre-alembic-backup.db
  $env:DATABASE_URL = "sqlite:///./barbearia-alembic.db"
  .\.venv\Scripts\python.exe -m alembic upgrade head
  .\.venv\Scripts\python.exe -m alembic current
  ```

  Mantenha `DATABASE_URL` apontando para o novo arquivo ao iniciar a API e validar o resultado. Preserve o arquivo original e o backup até confirmar que não precisa dos dados antigos. Não use `stamp` nem tente completar schemas parciais automaticamente.
- **Schema incompatível ou versão desconhecida:** a migração falha e o startup avisa que a revisão precisa ser aplicada. Preserve o banco, faça backup e investigue separadamente; não remova tabelas/dados para forçar a atualização.

O downgrade da revisão baseline está desabilitado porque retornar a um schema sem as tabelas da aplicação apagaria dados. Para desenvolvimento, restaure o backup ou crie outro banco vazio e reaplique `upgrade head`; downgrade não substitui backup.

#### Testes de integração PostgreSQL

Os testes usam SQLite temporário por padrão, mesmo que `BOOKING_TEST_POSTGRES_URL` esteja definida. Para habilitar PostgreSQL, configure **ambas** `BOOKING_TEST_BACKEND=postgresql` e `BOOKING_TEST_POSTGRES_URL` com uma URL `postgresql+psycopg://` cujo nome de banco termine em `_test`. O suporte não usa `DATABASE_URL` nem lê `.env` para escolher o banco de teste. Antes de criar qualquer schema, valida a autenticação e confirma o banco e usuário conectados; depois cria um schema `barbearia_test_*` exclusivo e remove somente esse schema ao terminar. O banco dedicado precisa permitir `CREATE SCHEMA` e `DROP SCHEMA`. Não aponte a URL a bancos de desenvolvimento ou produção.

O projeto fornece `compose.postgres-test.yml` para um PostgreSQL efêmero, ligado somente a `127.0.0.1:55432`, sem volume persistente. A configuração não foi iniciada automaticamente. No PowerShell, depois de instalar manualmente as dependências do `requirements.txt` e ter Docker Compose disponível:

```powershell
$env:POSTGRES_TEST_PASSWORD = (& .\.venv\Scripts\python.exe -c 'import secrets; print(secrets.token_urlsafe(24))')
docker compose -f ..\compose.postgres-test.yml up -d --wait
$env:BOOKING_TEST_POSTGRES_URL = "postgresql+psycopg://barbearia_test:$($env:POSTGRES_TEST_PASSWORD)@127.0.0.1:55432/barbearia_test"
$env:BOOKING_TEST_BACKEND = "postgresql"
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_postgres_booking_migration.py" -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_schema_migrations.py" -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_booking_integrity.py" -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_booking_temporal.py" -v
$env:BOOKING_TEST_BACKEND = "sqlite"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Com `BOOKING_TEST_BACKEND=postgresql`, os testes de integridade concorrente e temporais executam contra PostgreSQL; cada requisição usa sua própria sessão/conexão. Os testes PostgreSQL de migração exercitam upgrade, preservação de registros, constraints e chaves estrangeiras, downgrade seguro e downgrade incompatível. Defina `BOOKING_TEST_BACKEND=sqlite` para a suíte SQLite, que continua usando arquivo temporário mesmo com a URL PostgreSQL presente. O serviço opcional pode ser encerrado com `docker compose -f ..\compose.postgres-test.yml down`; não remova volumes manualmente.

### 2. Criar dados locais de demonstração

Com o backend em execução, acesse:

```text
http://127.0.0.1:8000/seed
```

Esse endpoint cria contas e serviços de demonstração se ainda não existirem. Credenciais locais:

| Perfil | E-mail | Senha |
| --- | --- | --- |
| Barbeiro | `barbeiro@barbearia.com` | `barbeiro123` |
| Cliente | `cliente@barbearia.com` | `cliente123` |

**Uso exclusivamente local:** `/seed` so e registrado com `APP_ENV=development`. Cria apenas barbeiro, cliente e servicos de demonstracao; nao cria administrador. As contas demo nao devem ser usadas em producao.

Crie o primeiro administrador manualmente depois de aplicar as migracoes: no diretorio `backend`, execute `python -m app.initial_admin` com `APP_ENV=development` para a instalacao SQLite local. O comando exige schema Alembic atualizado, pede nome/e-mail e solicita a senha sem eco. Em producao use `APP_ENV=production` e PostgreSQL. O processo permite somente um administrador inicial.

### 3. Servir o frontend

Em outro terminal, na raiz do repositório:

```powershell
python -m http.server 5500
```

Abra `http://127.0.0.1:5500/frontend/pages/index.html`. O fallback dos fontes do frontend continua sendo `http://127.0.0.1:8000`, configurado em `installation-config.mjs`; `window.BARBEARIA_API_URL` continua disponível como override antes dos módulos. Para o build hospedado do Render, use `PUBLIC_API_URL`; `build-static.mjs` injeta essa origem pública no artefato sem editar arquivos do frontend.

## Variáveis de ambiente

O arquivo `backend/.env.example` contém os valores iniciais. Copie-o para `backend/.env` e ajuste conforme seu ambiente:

| Variável | Finalidade | Padrão local |
| --- | --- | --- |
| `DATABASE_URL` | URL de conexão SQLAlchemy | `sqlite:///./barbearia.db` |
| `CORS_ALLOWED_ORIGINS` | Origens web explicitamente autorizadas, separadas por vírgula | `http://127.0.0.1:5500` em desenvolvimento; obrigatória em produção, com uma ou mais origens HTTPS reais do frontend |
| `SECRET_KEY` | Chave privada de assinatura JWT, com pelo menos 32 bytes UTF-8 | Obrigatória; não há valor padrão |
| `ALGORITHM` | Algoritmo JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Validade do token de acesso em minutos (faixa 5–60) | `15` minutos |
| `TERMS_VERSION` | Versão dos termos de consentimento LGPD registrada no cadastro | `1.0` |
| `CLIENT_IP_SOURCE` | Origem do IP para rate limit/auditoria: `direct` (padrão, ignora headers) ou `cf-connecting-ip` (um IP validado do edge confiável) | `direct` |
| `RATE_LIMIT_MAX_ATTEMPTS` | Limite legado por IP/rota nos endpoints protegidos exceto login | `5` |
| `RATE_LIMIT_BLOCK_MINUTES` | Janela legada dos endpoints protegidos exceto login | `15` minutos |
| `RETENTION_DAYS` | Retenção de eventos de auditoria antes de expurgo | `365` dias |
| `METRICS_TOKEN` | Token bearer de pelo menos 32 caracteres aleatorios para scraping Prometheus | Vazio (desabilita `/metrics`) |
| `FORCE_HTTPS` | Redireciona requisições HTTP; padrão ligado em produção e desligado em desenvolvimento/teste | Derivado de `APP_ENV` |
| `APP_ENV` | Ambiente de execução | Obrigatória: use `development`, `test` ou `production`; implantações devem usar exatamente `production` |
| `SCHEDULING_TIMEZONE` | Fuso IANA da instalação | `America/Sao_Paulo` local; obrigatório em produção |
| `EMAIL_TRANSPORT` | Transporte de recuperação: `smtp` ou `brevo_api` | `smtp` (compatível com instalações existentes) |
| `BREVO_API_KEY`, `EMAIL_FROM` | Chave secreta e endereço de remetente autorizado na Brevo | Obrigatórios em produção com `brevo_api`; chave somente no backend/painel, nunca no repositório |
| `EMAIL_TIMEOUT_SECONDS` | Timeout HTTPS da Brevo | `10` segundos, maior que zero e até `120` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` | Transporte e remetente para redefinição de senha | Com `smtp`, host e remetente obrigatórios em produção; usuário/senha devem ser fornecidos juntos e podem ficar vazios para relay sem autenticação |
| `SMTP_TIMEOUT_SECONDS` | Timeout da conexão SMTP | `10` segundos |
| `PASSWORD_RESET_URL` | URL pública da página `reset.html` | Opcional em desenvolvimento; obrigatória em produção, HTTPS e na origem listada em CORS |

O envio de redefinição usa o transporte selecionado: SMTP com STARTTLS ou a [API transacional HTTPS da Brevo](https://developers.brevo.com/reference/send-transac-email). Em produção, a API valida somente as opções do transporte selecionado e exige URL HTTPS de redefinição na origem permitida por CORS. Configure usuário e senha SMTP em conjunto quando o relay exigir autenticação; na Brevo, use uma chave de API (não SMTP) e `EMAIL_FROM` com apenas o endereço autorizado do remetente. Em desenvolvimento, e-mail é opcional; sem entrega aceita pelo transporte, a resposta continua genérica e nenhum novo token utilizável é persistido. Os links colocam o token no fragmento da URL, que não é enviado na requisição HTTP da página.

Gere uma chave uma única vez e guarde-a em `backend/.env` (não gere uma chave nova a cada inicialização):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copie o resultado para `SECRET_KEY` em `backend/.env`. A aplicação falha ao iniciar se a chave estiver ausente, curta, de baixa diversidade ou parecer um valor de exemplo/desenvolvimento/teste. O `.env.example` deixa essa variável vazia intencionalmente. Use uma chave persistente e privada por ambiente; não envie `.env` ao Git. Em produção, configure também HTTPS, restrinja CORS e não use as credenciais de demonstração.

Para PostgreSQL, defina `DATABASE_URL` com a URL SQLAlchemy do banco. Em produção, `postgresql://` é normalizada para o driver `postgresql+psycopg`; a conexão remota adiciona `sslmode=require` quando nenhum modo TLS é informado e rejeita modos inseguros explícitos. O `backend/requirements.txt` instala `psycopg[binary]`. SQLite é aceito somente em desenvolvimento e testes.

O access token JWT tem validade padrão de 15 minutos (configurável entre 5 e 60) e permanece em `localStorage` para a navegação entre páginas; JavaScript injetado na origem, como em um XSS, pode lê-lo. O refresh token aleatório é armazenado no servidor somente como SHA-256 e enviado exclusivamente em cookie `HttpOnly`, `SameSite=Lax` e `Secure` em produção, com `Path=/auth` e duração de 30 dias. O JSON de login contém `access_token`, `token_type` e `user`; o refresh retorna apenas `access_token` e `token_type`, com rotação no cookie. Consumidores externos que liam `refresh_token` no JSON precisam usar o cookie. As chamadas usam `credentials: include`; em produção, site e API precisam compartilhar o mesmo domínio registrável (por exemplo, `app.dominio.com` e `api.dominio.com`). `/auth/refresh` e `/auth/logout` aceitam somente `Origin` listado em `CORS_ALLOWED_ORIGINS`.

Access tokens usam `sub` como o ID imutável da conta em string decimal positiva, nunca e-mail. Assinatura, expiração e estado ativo/bloqueado continuam obrigatórios. Tokens legados cujo `sub` é e-mail recebem 401, sem fallback; um refresh válido pode emitir access token no novo formato, caso contrário é necessário novo login. Reutilizar o e-mail de uma conta excluída não transfere seus tokens; alterar o e-mail de uma conta ativa mantém o vínculo ao mesmo ID, nunca à nova conta que reutilizar o endereço.

Antes de emitir sessão, o login faz UPDATE condicional pelo ID e hash originalmente verificado, inclusive quando o hash não precisa de upgrade. O lock dessa atualização é mantido até o commit da sessão. Se uma recuperação concorrente já alterou a credencial, a atualização não encontra a linha, a transação é desfeita e o login retorna 401 sem tokens/cookie. O upgrade bcrypt → Argon2 continua disponível quando não há conflito. Não há mudança de schema ou de formato dos refresh tokens e tokens de recuperação.

Subdomínios distintos de `onrender.com` são cross-site: `onrender.com` consta na [Public Suffix List](https://publicsuffix.org/list/public_suffix_list.dat). Nesse cenário, `SameSite=Lax` impede refresh por fetch, mesmo com CORS e `credentials: include` ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch)). A solução F1 preparada neste repositório serve frontend e API na origem HTTPS do mesmo serviço Python, mantendo Lax e dispensando DNS/proxy novos. A aplicação do Blueprint e a validação publicada ainda são necessárias. Não relaxe `SameSite` para contornar essa incompatibilidade.

Na seleção de data do cliente, o frontend valida `YYYY-MM-DD`, o calendário e a janela de hoje até o dia 14 em `America/Sao_Paulo` antes de consultar disponibilidade. Digitação incompleta não consulta a API e remove horários antigos. Na confirmação, o limite considera o horário exato atual mais 14 dias; o backend permanece responsável por disponibilidade, concorrência e todas as regras definitivas. O relógio do dispositivo pode divergir do servidor.

### Admissão de login e revogação de sessões

**F1 — origem única:** `SERVE_FRONTEND=true` publica `/pages` e `/assets` no FastAPI e configura o frontend com a própria origem. Nesse modo `/` redireciona à home; no modo API-only padrão o contrato JSON permanece. CORS deve listar exatamente essa origem; cookies continuam HttpOnly/Secure em produção/SameSite=Lax/Path=/auth, sem Domain ou cookies de terceiros. `render.yaml` prepara essa topologia e o redirecionamento do site estático antigo. A implantação e validação real Render ainda são necessárias; consulte [procedimento F1](docs/security/AUTH_F1_SAME_ORIGIN.md). Não houve deploy nesta correção.

Correção F2: o login publica um marcador interno após confirmar CAS, sessão e sucesso da reserva. O middleware dispensa a finalização redundante dessa reserva, preservando a resposta com cookie mesmo se o armazenamento de finalização estiver indisponível. Falhas anteriores mantêm rollback/finalização condicional. Entrega HTTP após commit e resultado de commit sem confirmação continuam sem garantia. Evidências em [F2_FIX.md](docs/validation-stage2/postgresql/F2_FIX.md).

**Decisão da etapa 2:** admissão distribuída por conta/IP e limite estrito de verificações por processo. A lease do banco não libera capacidade de hash local. A ordem User antes do consumo de token de recuperação foi corrigida. Consulte [garantias e procedimento de implantação da etapa 2](docs/security/AUTH_STAGE2_ROLLOUT.md), incluindo a validação PostgreSQL pendente e a barreira necessária contra versões mistas.

`POST /auth/login` reserva a tentativa em `login_attempts` antes da senha. O e-mail normalizado é guardado apenas como HMAC com separação de domínio e SECRET_KEY; contadores não recebem senhas, tokens nem e-mail em claro. Um sucesso não reinicia falhas de outras contas. Falhas/reservas por conta têm janela curta para limitar bloqueios provocados por terceiros, e o IP tem orçamento maior para redes compartilhadas.

| Variáveis LOGIN_RATE_* | Padrões | Controle |
|---|---|---|
| ACCOUNT_FAILURES / ACCOUNT_WINDOW_SECONDS | 5 / 60s | Falhas e reservas por conta, mesmo com IPs diferentes |
| IP_FAILURES / IP_WINDOW_SECONDS | 30 / 300s | Falhas e reservas por IP/rota |
| IP_REQUESTS / REQUEST_WINDOW_SECONDS | 60 / 60s | Todas as tentativas por IP/rota, inclusive sucessos e payload inválido |
| ACCOUNT_CONCURRENCY / IP_CONCURRENCY | 2 / 4 | Reservas simultâneas por conta e IP |
| LEASE_SECONDS | 120s | Recuperação de reservas abandonadas |

`AUTH_PASSWORD_MAX_CONCURRENCY` controla separadamente verificações simultâneas por processo: padrão **1**, inteiro de **1 a 16**, validado ao iniciar. Alterações exigem reinício. Use capacidade proporcional à memória/CPU; não é recomendação de aumentar paralelismo no plano free. O verificador comum usa semáforo não bloqueante: saturação retorna 503 genérico com Retry-After=1, sem fila adicional aguardando esse semáforo. Login e confirmação de senha compartilham a capacidade; verificação bcrypt e upgrade Argon2 ocupam a mesma vaga até o fim. Geração de hashes em cadastro/reset não integra esse teto de verificações; parâmetros criptográficos não foram reduzidos.

Use o prefixo completo, por exemplo `LOGIN_RATE_ACCOUNT_FAILURES`. Valores são validados na inicialização e precisam ser consistentes entre processos, assim como SECRET_KEY. Trocar a chave reinicia a identidade dos contadores por conta; o histórico por IP permanece. Os padrões permitem uso normal de uma barbearia pequena sem bloqueio global. Ataques distribuídos por muitas contas e IPs ainda podem exigir proteção do edge.

Admissão usa locks transacionais ordenados por conta/IP no PostgreSQL (READ COMMITTED explícito) e BEGIN IMMEDIATE no SQLite. A transação termina antes da senha; não há contador distribuído somente em memória. Cinco falhas normalmente retornam 401; a tentativa que excede o orçamento retorna 429 genérico com Retry-After em segundos, sem revelar existência da conta. Tentativas bloqueadas não prolongam a janela. Falha do armazenamento retorna 503 genérico com Retry-After=1 antes da senha na admissão.

Reservas vivas ocupam provisoriamente o orçamento de admissão. A revisão `20261107_02` distingue `pendente`, `sucesso`, `credencial_rejeitada` e `neutro`, com motivo de finalização fechado. Saturação/indisponibilidade sem rejeição conhecida, payload inválido e encerramento sem veredicto são neutros: permanecem no limite geral de requisições, sem consumir cotas de senha incorreta e sem marcar sucesso. O resultado vem da decisão de autenticação, não do status HTTP. Uma rejeição real já conhecida não é apagada por erro, cancelamento ou expiração posteriores; portanto um erro HTTP posterior a essa rejeição não transforma a tentativa em neutra. Rejeição por rate limiting ocorre antes de criar reserva e não prolonga janelas.

Após expiração da lease, reservas novas ainda sem veredicto deixam de ocupar admissão distribuída; o expurgo de histórico com mais de 30 dias permanece. O hash ativo mantém sua vaga local até retornar ou falhar, mesmo com cancelamento HTTP ou lease vencida. Não existe interrupção forçada de thread: trabalho travado mantém a vaga até terminar ou o processo ser efetivamente encerrado. Processo novo recebe capacidade local nova; reservas do processo encerrado recuperam-se pelas janelas/lease existentes.

O teto agregado é a soma das capacidades dos processos realmente vivos, inclusive versões sobrepostas; não há coordenador global. Relógios devem estar sincronizados. Após o CAS de User, o login consome condicionalmente sua reserva ainda ativa/não expirada na mesma transação da sessão. Expiração, invalidação anterior ao consumo ou cancelamento observado antes da autorização impedem tokens/cookie e desfazem o upgrade. A autorização é linearizada nesse consumo; cancelamento concorrente ao commit pode ocorrer depois da última checagem e não garante rollback nem revogação retroativa de sessão confirmada. O cliente cancelar/desconectar também não prova interrupção do hash. Filas já existentes do servidor, pool de threads e conexões não são limitadas por esse semáforo.

A revisão aditiva `20261107_01`, encadeada a `20261031_01`, adiciona somente account_key, em_andamento, expira_em e índice de conta/rota/tempo em login_attempts. Histórico fica intacto, identidade/expiração antigas ficam nulas e em_andamento começa false. Upgrade deve ocorrer antes de executar esta versão em produção, pelo fluxo Alembic existente. Downgrade destrutivo é recusado antes de DDL, como nas revisões anteriores; recuperação é forward-only. Não executar create_all em produção.

A revisão aditiva `20261107_02`, após `20261107_01`, acrescenta `resultado` e `motivo_finalizacao` opcionais, sem alterar revisões anteriores, dados ou índices. Resultado NULL identifica legado e mantém a interpretação binária conservadora (`sucesso=False` ocupa o orçamento anterior até a janela original expirar); não se inventa se um erro histórico foi senha incorreta ou indisponibilidade. Nenhum histórico é reclassificado por backfill. Para novos registros, finalização usa UPDATE somente quando resultado=pendente: término repetido não sobrescreve resultado terminal. Sucesso é gravado junto da sessão e do CAS, com rollback conjunto em falha. O deploy deve atingir `20261107_02`; convivência com writers antigos continua proibida pelo roteiro operacional.

Refresh, logout, replay, reset e bloqueio compartilham a ordem de lock User → RefreshToken. Refresh relê o token depois de esperar pelo lock; logout revoga sua família, inclusive sucessores, sem encerrar famílias independentes. Um cookie de resposta tardia pode reaparecer no navegador, mas não consegue renovar uma família encerrada. Origin e atributos do cookie permanecem inalterados; frontend não foi modificado.

Access JWTs já emitidos permanecem válidos até expirar após logout/reset (padrão15min, configurável5–60min). Esta etapa revoga a renovação, sem blacklist ou consulta adicional por requisição; a consulta existente continua verificando conta ativa/bloqueada. Portanto um access token já emitido, inclusive por resposta atrasada, pode continuar utilizável nessa janela. Revogação imediata por sessão exigiria outro desenho e não foi implementada.

O modo direct ignora headers encaminhados. O Blueprint declara cf-connecting-ip, mas apenas validar a sintaxe do header não autentica o proxy: sua confiança depende de todo acesso passar pelo edge que o sobrescreve e da ausência de bypass. A infraestrutura publicada não foi consultada/testada; não há comprovação operacional desse requisito, nem de entrega de cookies em navegador ou de concorrência em PostgreSQL nesta entrega.

As garantias de coordenação pressupõem que todos os processos/instâncias usem esta versão e a mesma política/chave. A migração preserva inserções antigas pelo default false, mas workers antigos não participam dos novos locks e limites; uma implantação futura deve considerar essa janela de versões mistas. Nenhuma implantação foi executada nesta etapa.

## Funcionalidades e requisitos

## Requisitos funcionais (RF)

A Tabela 1 detalha os 24 requisitos funcionais que compõem o escopo de funcionalidades do sistema de agendamento para barbearias. Os requisitos RF23 e RF24 foram incluídos para atender, respectivamente, às necessidades de auditoria e aos direitos do titular de dados previstos na LGPD.

**Tabela 1 – Requisitos funcionais (RF)**

| **Código** | **Requisito Funcional** | **Descrição Detalhada** | **Perfil / Módulo** |
| --- | --- | --- | --- |
| RF01 | Catálogo Público | Exibir catálogo público de serviços oferecidos com preço, descrição e duração estimada. | Público |
| RF02 | Informações Institucionais | Exibir endereço, mapa interativo, formas de contato e horário de funcionamento. | Público |
| RF03 | Nota Média de Avaliações | Exibir a nota média pública calculada a partir das avaliações aprovadas. | Público |
| RF04 | Cadastro de Cliente | Permitir a criação de conta de cliente com coleta explícita e registro do consentimento LGPD (versão dos termos, data/hora, IP de origem e origem do consentimento). | Cliente |
| RF05 | Autenticação e Autorização | Autenticar usuários (Cliente, Barbeiro, Admin) via JWT com controle RBAC, incluindo access token curto, renovação por refresh token revogável e encerramento de sessão (logout). | Geral |
| RF06 | Recuperação de Senha | Solicitar e processar a redefinição de senha por token de uso único e tempo limite. A resposta é idêntica exista ou não o e-mail; o envio depende de integração com provedor de e-mail. | Geral |
| RF07 | Consulta de Horários | Consultar horários livres filtrando por serviço, profissional e data (RN-01). | Cliente / Admin |
| RF08 | Agendamento de Serviço | Permitir a reserva de serviço, profissional, data e horário específico. | Cliente / Admin |
| RF09 | Cancelamento de Reserva | Permitir o cancelamento de agendamentos respeitando a antecedência mínima de 24h (RN-02). | Cliente / Admin |
| RF10 | Reagendamento de Reserva | Permitir a alteração de data/horário respeitando limites de até 2 reagendamentos (RN-02). | Cliente / Admin |
| RF11 | Histórico do Cliente | Exibir o histórico completo de agendamentos passados e futuros do cliente. | Cliente |
| RF12 | Avaliação do Atendimento | Permitir que o cliente avalie com nota e comentário atendimentos concluídos (RN-04). | Cliente |
| RF13 | Consulta de Agenda | Exibir horários, clientes, serviços, profissionais e status do dia selecionado; o barbeiro visualiza apenas a própria agenda e o admin visualiza a agenda de toda a equipe. A interface permite selecionar datas da semana atual. | Barbeiro / Admin |
| RF14 | Registro de Atendimento | Aplicar transições válidas: pendente para confirmado/cancelado; confirmado para concluído/falta/cancelado; concluído para avaliado somente pela avaliação do cliente dono. Cliente cancela com 24h de antecedência; conclusão e falta só após o início. | Cliente / Barbeiro / Admin |
| RF15 | Agendamento Manual/Avulso | Permitir ao admin/barbeiro realizar agendamentos manuais para clientes sem cadastro. | Admin / Barbeiro |
| RF16 | Gestão de Serviços | Permitir cadastrar, editar, listar e remover serviços, preços e durações. | Admin |
| RF17 | Associação Barbeiro-Serviço | Vincular ou remover a capacitação de um barbeiro para realizar determinados serviços. | Admin |
| RF18 | Jornadas e Bloqueios | Configurar jornadas semanais de trabalho, folgas, feriados e bloqueios temporários. | Admin / Barbeiro |
| RF19 | Gestão de Clientes | Consultar, editar perfil, bloquear e desbloquear contas de clientes; o bloqueio invalida as sessões ativas. | Admin |
| RF20 | Gestão Institucional | Atualizar endereço, horário de funcionamento e informações gerais da barbearia. | Admin |
| RF21 | Relatório Financeiro | Emitir relatórios de faturamento por período com base nos atendimentos concluídos. | Admin |
| RF22 | Moderação de Avaliações | Ocultar ou reexibir avaliações públicas com conteúdo inadequado. | Admin |
| RF23 | Auditoria de Eventos | Consultar os registros de auditoria (autenticação, cancelamentos e ações administrativas), filtrando por usuário, ação e período. | Admin |
| RF24 | Exportação de Dados Pessoais | Permitir ao cliente exportar seus dados cadastrais e de agendamentos em formato estruturado (portabilidade, LGPD art. 18). | Cliente |

## Requisitos não funcionais (RNF)

A Tabela 2 apresenta os 18 Requisitos Não-Funcionais, organizados por categoria. Os requisitos RNF-01 a RNF-10 compõem a especificação original e foram detalhados quanto à segurança; os requisitos RNF-11 a RNF-18 foram acrescentados para cobrir validação de entradas, CORS, gestão de segredos, auditoria, backup, dependências, monitoramento e recuperação de desastres, conforme práticas recomendadas por OWASP (2021) e pela norma ABNT NBR ISO/IEC 27002 (ABNT, 2022).

**Tabela 2 – Requisitos não-funcionais (RNF)**

| **Código** | **Categoria** | **Requisito Não-Funcional** | **Detalhamento Técnico** |
| --- | --- | --- | --- |
| RNF-01 | Desempenho | Serialização e Isolamento de Agendamentos | Garantir a atomicidade na reserva/reagendamento utilizando locks de software na aplicação (booking.py) ou transações isoladas no banco, eliminando o double booking. |
| RNF-02 | Segurança | Proteção Criptográfica de Credenciais | Senhas novas usam Argon2id; bcrypt legado continua verificável e é atualizado no login. JWT tem expiração curta e configurável (ACCESS_TOKEN_EXPIRE_MINUTES, padrão 15 minutos, faixa de 5 a 60) e refresh token opaco, aleatório, rotativo e revogável, persistido somente como SHA-256. Cookie HttpOnly, SameSite=Lax e Secure em produção; refresh/logout validam Origin contra CORS. SECRET_KEY é obrigatória em todos os ambientes. |
| RNF-03 | Usabilidade | Responsividade Mobile-First | Interface desenvolvida em HTML5/CSS3 Vanilla responsiva com Media Queries, sem quebras de layout em telas a partir de 320px de largura. |
| RNF-04 | Confiabilidade | Conformidade Técnica com LGPD | Registro explícito do consentimento no cadastro (versão dos termos, data/hora, IP e origem) e endpoint DELETE /users/me para anonimização irreversível dos dados pessoais do cliente, preservando os registros financeiros sem identificação. Exportação dos dados do titular (RF24). |
| RNF-05 | Segurança | Controle de Acesso por Perfis (RBAC) | Interceptação das requisições privadas no FastAPI validando o perfil (RoleEnum: CLIENTE, BARBEIRO, ADMIN) por dependência centralizada e a propriedade do recurso: o cliente acessa apenas os próprios agendamentos e o barbeiro, apenas a própria agenda. |
| RNF-06 | Segurança | Comunicação Criptografada | Toda comunicação entre o frontend JavaScript e a API FastAPI deve utilizar obrigatoriamente HTTPS/TLS 1.3 em produção, com cabeçalho HSTS, redirecionamento de HTTP para HTTPS e cabeçalhos de segurança (CSP e X-Content-Type-Options). |
| RNF-07 | Segurança | Proteção contra Força Bruta | Rate Limiting nas rotas /auth/login, /auth/register, /auth/esqueci-senha e /auth/redefinir-senha, bloqueando requisições do IP por período configurável após 5 tentativas incorretas consecutivas. |
| RNF-08 | Desempenho | Tempo de Resposta da API | Endpoint GET /appointments/disponiveis deve processar e responder em tempo máximo de 500ms em condições normais de rede. |
| RNF-09 | Compatibilidade | Compatibilidade de Navegadores | Meta: frontend com ES Modules nativos em Chrome, Firefox, Safari e Edge. A validação do Ritual está demonstrada em Chrome/Edge; Firefox/Safari continuam com limites de evidência registrados em docs/HOME_MOTION_INTEGRATION.md. |
| RNF-10 | Arquitetura | Persistência e Migração Transparente | Abstração ORM via SQLAlchemy permitindo transição transparente entre SQLite (desenvolvimento) e PostgreSQL (produção). Evolução do esquema por migrations versionadas (Alembic), com scripts de upgrade e downgrade que permitam rollback. |
| RNF-11 | Segurança | Validação e Sanitização de Entradas | Validação de tipos, formatos e tamanhos de todos os campos por schemas Pydantic; escape do conteúdo enviado por usuários (ex.: comentários de avaliações) na saída do frontend; consultas exclusivamente parametrizadas via ORM, sem concatenação de SQL, prevenindo SQL Injection e XSS. |
| RNF-12 | Segurança | Política de CORS Restrita | A API aceita requisições apenas das origens listadas em CORS_ALLOWED_ORIGINS, sem uso de curinga (*) em produção, com métodos e cabeçalhos explicitamente permitidos. |
| RNF-13 | Segurança | Gestão de Segredos | Segredos (SECRET_KEY, DATABASE_URL, credenciais de e-mail) mantidos somente em variáveis de ambiente, fora do repositório, com valores distintos por ambiente, validação na inicialização e rotação periódica. Dados de demonstração (seed) desabilitados em produção. |
| RNF-14 | Confiabilidade | Registro de Logs e Auditoria | Registro estruturado de eventos de autenticação (sucesso e falha), cancelamentos e ações administrativas, com usuário, ação, entidade, IP e data/hora, sem armazenar senhas ou tokens, e com período de retenção definido. |
| RNF-15 | Confiabilidade | Backup e Retenção de Dados | Backup automático diário do banco de dados, com retenção mínima de 30 dias, armazenamento em local distinto do servidor de aplicação e teste periódico de restauração. |
| RNF-16 | Manutenibilidade | Gestão de Dependências | Versões fixadas em requirements.txt, auditoria periódica de vulnerabilidades (pip-audit) e atualização automatizada de dependências (Dependabot). |
| RNF-17 | Operação | Monitoramento e Observabilidade | /health verifica o processo; /ready verifica banco e revisão Alembic. Métricas de latência/erros e procedimentos estão implementados; configuração e teste de alertas externos dependem da operação. |
| RNF-18 | Confiabilidade | Plano de Recuperação de Desastres | Plano documentado de recuperação com RPO máximo de 24 horas e RTO máximo de 4 horas, incluindo procedimento de restauração passo a passo e responsáveis. |

## Regras de negócio (RN)

As regras de negócio definem restrições do domínio que os requisitos funcionais devem respeitar. A Tabela 3 apresenta as cinco regras vigentes, os requisitos que as utilizam e o ponto do código em que são aplicadas.

**Tabela 3 – Regras de negócio (RN)**

| **Código** | **Regra de negócio** | **RF relacionados** | **Implementação** |
| --- | --- | --- | --- |
| **RN-01** | Um horário disponível deve estar dentro da jornada, sem bloqueio ou conflito e comportar a duração do serviço. | RF07, RF08, RF15 | validate_booking_slot (booking.py) |
| **RN-02** | O cliente precisa cancelar ou reagendar com pelo menos 24 horas de antecedência. Cada agendamento permite até 2 reagendamentos. | RF09, RF10 | appointments.py; Appointment.reschedule_count |
| **RN-03** | Agendamentos podem ser feitos com até 14 dias de antecedência. | RF08 | BOOKING_WINDOW_DAYS = 14 |
| **RN-04** | Apenas o dono de um agendamento concluído pode avaliá-lo, uma única vez. | RF12 | Avaliacao.appointment_id (único) |
| **RN-05** | O agendamento mantém um instantâneo do preço e da duração do serviço no momento da criação. | RF08, RF21 | Appointment.preco e duracao_minutos |

## Telas do frontend

- `index.html`: página inicial pública, catálogo, informações institucionais e avaliações.
- `catalog.html`: catálogo de serviços.
- `cadastro.html`, `login.html`, `forgot.html`, `reset.html`: cadastro, autenticação e recuperação/redefinição de senha.
- `client-services.html`, `client-profissional.html`, `client-date.html`, `client-confirm.html`: etapas do agendamento.
- `client-dashboard.html`, `client-appointments.html`, `client-evaluate.html`, `client-account.html`: painel, histórico, avaliação e conta do cliente.
- `admin.html`: agenda, gestão de serviços/equipe/clientes, jornadas/bloqueios, informações, avaliações e financeiro.

## API

Todos os endpoints são servidos pelo FastAPI na porta `8000`. Rotas protegidas recebem `Authorization: Bearer <token>`.

| Grupo | Rotas principais | Acesso |
| --- | --- | --- |
| Saude | `GET /`, `GET /health`, `GET /ready` | Publico; `/health` verifica o processo e `/ready` exige banco e revisao Alembic atual |
| Autenticação | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/esqueci-senha`, `POST /auth/redefinir-senha` | Conforme operação |
| Serviços | `GET /services/`, `GET /services/{service_id}` | Público |
| Serviços (gestão) | `POST /services/`, `PUT /services/{service_id}`, `DELETE /services/{service_id}` | Administrador |
| Agendamentos | `GET /appointments/`, `GET /appointments/disponiveis`, `POST /appointments/`, `GET/PUT/DELETE /appointments/{appointment_id}` | Autenticado e/ou dono/equipe |
| Avaliações | `GET /appointments/avaliacoes`, `POST /appointments/{appointment_id}/avaliacao` | Leitura pública; escrita pelo cliente dono |
| Administração | `POST /admin/agendamentos`, `GET /admin/agenda`, `GET /admin/me/agenda`, `GET /admin/relatorio` | Administrador ou barbeiro, conforme rota |
| Moderação | `GET /admin/avaliacoes`, `PATCH /admin/avaliacoes/{avaliacao_id}/ocultar` | Administrador |
| Institucional | `GET /informacoes/`, `POST /informacoes/`, `PUT /informacoes/` | Leitura pública; escrita administrativa |
| Usuários | `GET /users/`, `GET /users/barbeiros`, `GET/PUT /users/{user_id}`, `DELETE /users/me` | Operações administrativas ou próprio usuário |
| Portabilidade | `GET /users/me/export`, `GET /users/me/export.pdf` | Cliente autenticado, dados da própria conta |
| Jornadas/bloqueios | `/horario/jornadas`, `/horario/bloqueios` | Administrador ou barbeiro dono |
| Serviços por barbeiro | `/barbeiro-servico/`, `/barbeiro-servico/barbeiro/{barbeiro_id}`, `/barbeiro-servico/servico/{service_id}/barbeiros` | Conforme perfil |
| Demonstração | `GET /seed` | Somente desenvolvimento |

`GET /admin/relatorio` retorna totais, quebras por barbeiro/serviço/dia e contagens de status; `GET /admin/relatorio/csv` exporta os atendimentos do período com neutralização de fórmulas em células CSV. Jornadas podem ser editadas, desativadas ou removidas por `PUT/DELETE /horario/jornadas/{jornada_id}`.

Consulte `/docs` para parâmetros, corpos de requisição e respostas completos.

## Organização do código

```text
backend/
├── app/
│   ├── main.py                 # Inicialização do FastAPI, CORS e routers
│   ├── database.py             # Engine/sessão e leitura da revisão; sem DDL no startup
│   ├── dependencies.py         # Dependência de usuário autenticado
│   ├── booking.py              # Validação de horário, conflito e serialização
│   ├── core/security.py        # Hash de senha e operações JWT
│   ├── models/user.py          # Modelos ORM e enums do domínio
│   ├── schemas/                # Schemas Pydantic de entrada e resposta
│   └── routers/                # Endpoints por domínio
├── alembic/                    # Revisões de schema
├── tests/                      # Testes Python e suporte a bancos descartáveis
└── requirements.txt

frontend/
├── assets/
│   ├── css/                    # Estilos gerais, home, cliente e painel admin
│   ├── js/                     # API, autenticação, agendamento e gestão
│   ├── media/home/             # Vídeo e poster locais do Ritual
│   └── images/
├── e2e/                        # Testes Playwright e Motion Lab (fora do build público)
├── tests/                      # Testes Node
├── scripts/                    # Build estático
└── pages/                      # Páginas HTML

docs/                          # Contratos, operação, evidências e material comercial
specs/                         # Decisões de produto confirmadas
tools/                         # Backup, novas instalações e helpers
```

## Classes do domínio (SQLAlchemy)

Definidas em `backend/app/models/user.py`:

| Classe | Responsabilidade |
| --- | --- |
| `User` | Cliente, barbeiro ou administrador; inclui status da conta e consentimento LGPD. |
| `Service` | Serviço oferecido, preço e duração padrão. |
| `Appointment` | Reserva, profissional, cliente (conta ou nome avulso), status, snapshot de preço/duração e valor cobrado. |
| `Avaliacao` | Nota, comentário e estado de moderação vinculados a um agendamento. |
| `InformacaoInstitucional` | Endereço, contato, mapa e horário da barbearia. |
| `JornadaTrabalho` | Horário semanal de atendimento de um barbeiro. |
| `BloqueioHorario` | Período indisponível para folga, feriado ou outro bloqueio. |
| `BarbearioServico` | Associação entre barbeiro e serviço que ele executa. |
| `PasswordResetToken` | Token de redefinição de senha, validade e uso. |
| `ConsentimentoLGPD` | Evidência de consentimento e versão dos termos. |
| `RefreshToken` | Sessão renovável, rotação, expiração e revogação. |
| `LoginAttempt` | Registro de tentativas para os controles de autenticação. |
| `AuditLog` | Eventos de autenticação e ações do domínio, com retenção configurável. |

Enums do domínio:

- `RoleEnum`: `CLIENTE`, `BARBEIRO`, `ADMIN`.
- `AppointmentStatusEnum`: `PENDENTE`, `CONFIRMADO`, `CONCLUIDO`, `CANCELADO`, `FALTA`, `AVALIADO`.

## Schemas Pydantic

Os schemas validam os dados HTTP; não são tabelas do banco. `ORMModel` configura leitura de atributos dos modelos ORM.

- **Base:** `ORMModel`.
- **Usuário/autenticação (`schemas/user.py`):** `UserBase`, `UserCreate`, `UserLogin`, `UserResponse`, `UserUpdate`, `EsqueciSenhaRequest`, `RedefinirSenhaRequest`, `Token`, `UserTokenResponse`.
- **Serviços (`schemas/service.py`):** `ServiceBase`, `ServiceCreate`, `ServiceUpdate`, `ServiceResponse`.
- **Agendamentos e avaliações (`schemas/appointment.py`):** `AppointmentBase`, `AppointmentCreate`, `AdminAppointmentCreate`, `AppointmentUpdate`, `AppointmentResponse`, `AvaliacaoBase`, `AvaliacaoCreate`, `AvaliacaoResponse`.
- **Jornadas e bloqueios (`schemas/horario.py`):** `JornadaTrabalhoBase`, `JornadaTrabalhoCreate`, `JornadaTrabalhoUpdate`, `JornadaTrabalhoResponse`, `BloqueioHorarioBase`, `BloqueioHorarioCreate`, `BloqueioHorarioUpdate`, `BloqueioHorarioResponse`.
- **Informações institucionais (`schemas/institucional.py`):** `InformacaoInstitucionalBase`, `InformacaoInstitucionalCreate`, `InformacaoInstitucionalUpdate`, `InformacaoInstitucionalResponse`.
- **Associação barbeiro-serviço (`schemas/barbeiro_servico.py`):** `BarbearioServicoBase`, `BarbearioServicoCreate`, `BarbearioServicoResponse`, `BarbearioServicoWithBarbeiroResponse`.

## Routers

- `auth.py`: cadastro, login, consulta da sessão e redefinição de senha.
- `services.py`: leitura pública e CRUD administrativo de serviços.
- `appointments.py`: disponibilidade, agendamento, cancelamento, reagendamento e avaliações.
- `admin.py`: agendamento manual, agenda da equipe, moderação e relatório financeiro.
- `users.py`: gestão de clientes, listagem de barbeiros e exclusão da própria conta.
- `horario.py`: jornadas e bloqueios.
- `barbeiro_servico.py`: associações entre profissionais e serviços.
- `institucional.py`: informações públicas e gestão institucional.

## Fuso horário da agenda

A agenda usa SCHEDULING_TIMEZONE (padrão America/Sao_Paulo). Datas sem offset na API continuam sendo horários locais da barbearia, como os valores datetime-local enviados pelo frontend. Datas recebidas com offset são convertidas para esse fuso antes de serem armazenadas no formato local sem fuso que o schema atual já utiliza. Respostas e parâmetros existentes permanecem compatíveis.

As colunas DateTime atuais não armazenam fuso horário; esta configuração não reinterpreta nem converte registros existentes. O sistema os continua tratando como horário local. Se houver suspeita de que dados históricos foram gravados como UTC ingênuo, faça inventário separado antes de qualquer conversão.

## Testes e validações

A suíte automatizada usa `unittest` e fica em `backend/tests`. Por padrão, ela executa com SQLite temporário e cobre configuração da aplicação, autenticação e autorização, recuperação de senha, regras temporais e integridade dos agendamentos, além da migração SQLite. Os testes específicos de PostgreSQL são ignorados quando o backend PostgreSQL não está explicitamente configurado.

Para validar também o PostgreSQL, configure `BOOKING_TEST_BACKEND=postgresql` e `BOOKING_TEST_POSTGRES_URL` para um banco exclusivo de testes, conforme as instruções acima. Nesse modo, os testes de integridade, concorrência, regras temporais e migração usam PostgreSQL; a suíte padrão não valida PostgreSQL quando essa configuração está ausente.

Para validar manualmente a API, use `http://127.0.0.1:8000/docs` e os dados locais de demonstração.

### Executar verificações frontend

Na raiz, instale as dependências fixadas no lockfile. Os testes da Estrelinha usam Three.js local do laboratório como fixture de rede; isso não muda a versão do import map de produção.

```powershell
npm ci --ignore-scripts
npm --prefix frontend/e2e/motion-lab ci --ignore-scripts
node node_modules/@playwright/test/cli.js install chromium firefox webkit
node --test "frontend/tests/*.test.mjs"
node node_modules/@playwright/test/cli.js test --config=frontend/e2e/home-experience.config.mjs --grep-invert "Ritual universal"
node node_modules/@playwright/test/cli.js test --config=frontend/e2e/ritual-continuous.config.mjs --project="chrome-*" --project="msedge-*"
node node_modules/@playwright/test/cli.js test --config=frontend/e2e/estrelinha-cinematic.config.mjs
```

As suites de apresentação acima servem arquivos estáticos e interceptam API fictícia; não iniciam backend nem banco. Os canais `chrome`/`msedge` requerem os navegadores correspondentes instalados. O config do Ritual também oferece Firefox/WebKit: executar sem filtro de projetos tenta todos os motores e atualmente registra as limitações de mídia/criação de página descritas no relatório.

A suíte completa de fluxos usa `frontend/e2e/playwright.config.mjs` e seu próprio ambiente de API/SQLite descartável; leia [as instruções E2E](frontend/e2e/README.md) antes de executá-la. Ela não deve usar banco local de desenvolvimento ou produção. Não há formatter/lint configurado no package.json raiz.

A agenda administrativa permite navegar por semanas mantendo o dia da semana
selecionado. Nos botões de data, as setas esquerda/direita selecionam dias,
PageUp/PageDown mudam sete dias e Home/End selecionam domingo/sábado. Falhas dos
catálogos auxiliares não impedem a consulta da agenda; erros da própria agenda
continuam visíveis. Clientes inativos/anonimizados não aparecem na gestão nem
podem ser consultados ou alterados por ID; bloqueados ativos continuam disponíveis.
As regressões de navegador dessa correção usam apenas servidor estático e API
fictícia interceptada, sem backend/migrações:
`node node_modules/@playwright/test/cli.js test --config=frontend/e2e/agenda-navigation.config.mjs`.

### Evidências e limites

Na rodada completa anterior de 2026-11-03: Node 27/27, HOME 44/44 e Ritual Chrome/Edge 22/22, com tempos intermediários, rVFC, reverso, touch e resize; fallback/reduced-motion WebKit 4/4. Reexecuções posteriores confirmaram o smoke Chrome/Edge; Firefox/WebKit continuam com os impedimentos documentados. Registros de backend/infraestrutura ficam em [requisitos](docs/REQUISITOS_STATUS.md); detalhes da HOME em [integração](docs/HOME_MOTION_INTEGRATION.md). Nada disso equivale a teste de produção ou em aparelhos físicos.

## Limitações e cuidados antes de produção

- O token de redefinição não é devolvido pela API nem gravado em logs da aplicação. Configure SMTP também para testar a recuperação localmente; sem entrega confirmada, o token não fica utilizável.
- O endpoint `GET /seed` só existe com `APP_ENV=development`; o processo recusa iniciar se `APP_ENV` estiver ausente ou inválido. A resposta não divulga credenciais.
- O CORS aceita apenas as origens normalizadas listadas em `CORS_ALLOWED_ORIGINS`. Em desenvolvimento, se a variável estiver ausente, é permitida a origem documentada `http://127.0.0.1:5500`. Em produção, a variável é obrigatória e deve conter uma ou mais origens HTTPS exatas do frontend publicado, incluindo a porta não padrão quando aplicável. Não use `*` nem inclua caminhos.
- Novas alterações de schema devem continuar sendo registradas em revisões Alembic e testadas em SQLite e PostgreSQL.
- Consentimento e anonimização implementados são controles técnicos; não substituem avaliação jurídica e operacional de conformidade com a LGPD.

## Homologação no Render

`render.yaml` descreve um Static Site e um Web Service Free com PostgreSQL independente. O build estático usa Node 22 para gerar a configuração pública da API. Referências `fromService` resolvem automaticamente `ALLOWED_HOSTS` pelo hostname público da API, `CORS_ALLOWED_ORIGINS` e `FRONTEND_ORIGIN` pela URL pública do frontend, e `PUBLIC_API_URL` pela URL pública da API. O `startCommand` compõe `PASSWORD_RESET_URL` como `${FRONTEND_ORIGIN}/pages/reset.html`, caminho confirmado em `frontend/pages/reset.html`; nenhuma URL precisa ser conhecida antes da criação dos serviços.

O Blueprint seleciona `EMAIL_TRANSPORT=brevo_api`, pois o Free bloqueia as portas SMTP usuais. O Render solicitará apenas `BREVO_API_KEY` (segredo) e `EMAIL_FROM` (endereço autorizado na Brevo), ambos fornecidos no painel; não os coloque no YAML nem no frontend. `SECRET_KEY` é gerada pelo Render e `DATABASE_URL` referencia o banco provisionado. SMTP permanece disponível para outras instalações. No Free, sem Shell/SSH ou `preDeployCommand`, o `startCommand` usa `python -m app.render_start`: executa Alembic até head, verifica a revisão e só então substitui o processo por Uvicorn. Falhas impedem o início da nova API, sem expor detalhes de conexão; `/ready` continua exigindo o head. A criação do administrador com `python -m app.initial_admin` permanece uma etapa operacional separada, indisponível via Shell no Free; este launcher não cria contas. A entrega real pela Brevo precisa ser validada após o provisionamento.

O build continua limitado à instalação de dependências. O launcher verifica migrações em cada início, inclusive após suspensão/reinício do Free; em head, Alembic não reaplica revisões. Novas migrações devem ser compatíveis com a versão anterior ainda atendendo tráfego durante o deploy (expand/contract). Como `/ready` exige revisão exata, avançar o schema pode tornar a instância antiga não pronta; este fluxo não garante zero downtime. Falha de deploy não desfaz migrações já confirmadas no banco; não faça downgrade automático. O fluxo pressupõe um único serviço migrador para esse banco e não instala migrations no lifespan ou em cada worker. Não compartilhe esse launcher entre serviços concorrentes sem coordenar a etapa de release. Migrações precisam terminar dentro da janela de inicialização do Render. O fluxo foi validado em SQLite e PostgreSQL 16 descartáveis, incluindo preservação de contas e bloqueio do servidor na falha de migração; o funcionamento online no Render continua pendente.

Auditoria RF23/RNF-14: o catálogo de eventos, metadados, filtros e testes está em [docs/AUDITORIA_RF23_RNF14.md](docs/AUDITORIA_RF23_RNF14.md). A persistência best-effort foi mantida; retenção tem dry-run e expurgo, cujo agendamento cabe à operação da instalação.

Operação inicial: backup/restauração com PostgreSQL 16, age, checksum e cópia por rsync foram validados em infraestrutura descartável; a retenção mínima de 30 dias é exigida pelo script. RNF-15, RNF-17 e RNF-18 permanecem parciais até definir executor/destino externo, configurar e testar alertas e identificar os responsáveis. Procedimentos e evidências em [monitoramento](docs/MONITORAMENTO.md) e [recuperação](docs/PLANO_RECUPERACAO_DESASTRES.md).

## Equipe

Projeto desenvolvido por estudantes de DSM da FATEC Itaquera. Consulte o histórico do repositório para autoria por alteração e contribuições.

## Desenvolvimento e documentação

Leia [AGENTS.md](AGENTS.md), [planos curtos](docs/superpowers/plans/README.md) e [workflow local](tools/codex-helpers/README.md#workflow-local-do-codex) para alterações assistidas por Codex. Graphify é uma ferramenta de navegação do código, sem dependência no runtime da aplicação. Outputs e caches locais precisam de triagem antes de versionamento.

O [material comercial](docs/business/notebooklm/00_INDICE.md) separa fatos do produto, hipóteses e planejamento; não descreve um SaaS multi-tenant implementado.


## Qualidade e acessibilidade — integração independente

Inclui nomes Unicode NFC em novas entradas, contratos de identidade de e-mail,
visibilidade acessível e seleção/elegibilidade administrativa de barbeiros.
Não inclui cooldown, fila ou mudanças de recuperação, JWT ou sessões.
Evidências e ressalvas em
[integração independente](docs/INTEGRACAO_QUALIDADE_AUTH_UX_INDEPENDENTE_20261104.md).
