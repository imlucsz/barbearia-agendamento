# Sistema de Agendamento Online para Barbearia

Projeto acadêmico do curso de Desenvolvimento de Software Multiplataforma (DSM) da FATEC Itaquera. O sistema reúne um site público, fluxo de agendamento para clientes e painel de gestão da barbearia.

## Tecnologias

- **Frontend:** HTML5, CSS3 responsivo e JavaScript ES Modules (Vanilla).
- **Backend:** Python, FastAPI, Pydantic e SQLAlchemy.
- **Banco de dados:** SQLite por padrão; PostgreSQL pode ser usado configurando a URL e instalando o driver correspondente.
- **Autenticação:** JWT Bearer (PyJWT); senhas novas com Argon2id e verificação compatível com hashes bcrypt existentes.

## Implantação por instalação

Para preparar uma barbearia com domínio, banco e configuração próprios, consulte [Implantação e reutilização](docs/IMPLANTACAO_E_REUTILIZACAO.md). O procedimento não copia dados de clientes nem configura multi-tenancy. O [inventário LGPD](docs/LGPD.md) descreve exportação, exclusão e retenção implementadas; revise as bases legais com assessoria jurídica.

Para criar um checkout limpo por barbearia, mapear personalizações e aplicar atualizações do núcleo, siga o [guia de reutilização e atualização](docs/REUTILIZACAO_E_ATUALIZACAO.md) e use os scripts em `tools/new-installation/`.

## Requisitos

- Python 3.10 ou superior (recomendado Python 3.11+).
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
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

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

`20261027_01` preserva a evolução histórica que remove a restrição antiga de `appointments(service_id, data_hora)`. A revisão `20261028_01` cria as nove tabelas do schema inicial; `20261029_01` adiciona consentimentos LGPD versionados e refresh tokens rotativos; `20261029_02` acrescenta tentativas de login; `20261029_03` acrescenta auditoria; `20261029_04` permite desvincular consentimentos e sessões revogadas durante anonimização; `20261029_05` adiciona a descricao publica dos servicos; `20261029_06` adiciona indices para consultas de disponibilidade. O schema atual tem treze tabelas. Em banco existente, a adoção só reconhece schemas suportados e falha sem apagar tabelas ou registros. Não há `stamp` automático.

Procedimento de adoção:

- **Banco novo PostgreSQL ou SQLite:** configure `DATABASE_URL` para o banco vazio exclusivo desta instalação e execute `python -m alembic upgrade head` antes de iniciar a API. A revisão `20261028_01` cria o schema legado de nove tabelas e `20261029_01` completa o schema atual com as duas tabelas de sessão/consentimento.
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
| `RATE_LIMIT_MAX_ATTEMPTS` | Falhas consecutivas por IP e rota antes do bloqueio | `5` |
| `RATE_LIMIT_BLOCK_MINUTES` | Duração do bloqueio das rotas de autenticação | `15` minutos |
| `RETENTION_DAYS` | Retenção de eventos de auditoria antes de expurgo | `365` dias |
| `METRICS_TOKEN` | Token bearer de pelo menos 32 caracteres aleatorios para scraping Prometheus | Vazio (desabilita `/metrics`) |
| `FORCE_HTTPS` | Redireciona requisições HTTP; padrão ligado em produção e desligado em desenvolvimento/teste | Derivado de `APP_ENV` |
| `APP_ENV` | Ambiente de execução | Obrigatória: use `development`, `test` ou `production`; implantações devem usar exatamente `production` |
| `SCHEDULING_TIMEZONE` | Fuso IANA da instalação | `America/Sao_Paulo` local; obrigatório em produção |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` | Transporte e remetente para redefinição de senha | O host e remetente são obrigatórios em produção; usuário/senha devem ser fornecidos juntos e podem ficar vazios para relay sem autenticação |
| `SMTP_TIMEOUT_SECONDS` | Timeout da conexão SMTP | `10` segundos |
| `PASSWORD_RESET_URL` | URL pública da página `reset.html` | Opcional em desenvolvimento; obrigatória em produção, HTTPS e na origem listada em CORS |

O envio de redefinição usa SMTP com STARTTLS. Em produção, a API não inicia sem host, remetente e URL HTTPS válida da página de redefinição. Configure usuário e senha SMTP em conjunto quando o relay exigir autenticação. Em desenvolvimento, SMTP é opcional; sem ele, a resposta de recuperação continua genérica e nenhum token utilizável é persistido. Os links colocam o token no fragmento da URL, que não é enviado na requisição HTTP da página. O `.env.example` contém somente opções locais e valores fictícios.

Gere uma chave uma única vez e guarde-a em `backend/.env` (não gere uma chave nova a cada inicialização):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copie o resultado para `SECRET_KEY` em `backend/.env`. A aplicação falha ao iniciar se a chave estiver ausente, curta, de baixa diversidade ou parecer um valor de exemplo/desenvolvimento/teste. O `.env.example` deixa essa variável vazia intencionalmente. Use uma chave persistente e privada por ambiente; não envie `.env` ao Git. Em produção, configure também HTTPS, restrinja CORS e não use as credenciais de demonstração.

Para PostgreSQL, defina `DATABASE_URL` com a URL SQLAlchemy do banco. Em produção, `postgresql://` é normalizada para o driver `postgresql+psycopg`; a conexão remota adiciona `sslmode=require` quando nenhum modo TLS é informado e rejeita modos inseguros explícitos. O `backend/requirements.txt` instala `psycopg[binary]`. SQLite é aceito somente em desenvolvimento e testes.

O access token JWT tem validade padrão de 15 minutos (configurável entre 5 e 60) e permanece em `localStorage` para a navegação entre páginas; JavaScript injetado na origem, como em um XSS, pode lê-lo. O refresh token aleatório é armazenado no servidor somente como SHA-256 e enviado ao frontend em cookie `HttpOnly`, `SameSite=Lax` e `Secure` em produção. As chamadas usam `credentials: include`; em produção, site e API precisam compartilhar o mesmo domínio registrável (por exemplo, `app.dominio.com` e `api.dominio.com`). `/auth/refresh` e `/auth/logout` aceitam somente `Origin` listado em `CORS_ALLOWED_ORIGINS`.

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
| RNF-02 | Segurança | Proteção Criptográfica de Credenciais | Hash de senhas via bcrypt antes da persistência. Tokens de acesso JWT assinados com HS256, com expiração curta e configurável (ACCESS_TOKEN_EXPIRE_MINUTES, padrão 15 minutos, faixa de 5 a 60) e renovação por refresh token opaco, aleatório, rotativo e revogável (persistir somente SHA-256; detectar reuso e revogar a família). O refresh token deve ser enviado em cookie HttpOnly, SameSite=Lax e Secure em produção; refresh/logout validam Origin contra CORS. A SECRET_KEY não possui valor padrão: a aplicação não inicia sem ela em produção. |
| RNF-03 | Usabilidade | Responsividade Mobile-First | Interface desenvolvida em HTML5/CSS3 Vanilla responsiva com Media Queries, sem quebras de layout em telas a partir de 320px de largura. |
| RNF-04 | Confiabilidade | Conformidade Técnica com LGPD | Registro explícito do consentimento no cadastro (versão dos termos, data/hora, IP e origem) e endpoint DELETE /users/me para anonimização irreversível dos dados pessoais do cliente, preservando os registros financeiros sem identificação. Exportação dos dados do titular (RF24). |
| RNF-05 | Segurança | Controle de Acesso por Perfis (RBAC) | Interceptação das requisições privadas no FastAPI validando o perfil (RoleEnum: CLIENTE, BARBEIRO, ADMIN) por dependência centralizada e a propriedade do recurso: o cliente acessa apenas os próprios agendamentos e o barbeiro, apenas a própria agenda. |
| RNF-06 | Segurança | Comunicação Criptografada | Toda comunicação entre o frontend JavaScript e a API FastAPI deve utilizar obrigatoriamente HTTPS/TLS 1.3 em produção, com cabeçalho HSTS, redirecionamento de HTTP para HTTPS e cabeçalhos de segurança (CSP e X-Content-Type-Options). |
| RNF-07 | Segurança | Proteção contra Força Bruta | Rate Limiting nas rotas /auth/login, /auth/register, /auth/esqueci-senha e /auth/redefinir-senha, bloqueando requisições do IP por período configurável após 5 tentativas incorretas consecutivas. |
| RNF-08 | Desempenho | Tempo de Resposta da API | Endpoint GET /appointments/disponiveis deve processar e responder em tempo máximo de 500ms em condições normais de rede. |
| RNF-09 | Compatibilidade | Compatibilidade de Navegadores | Frontend construído com ES Modules nativos, executando sem necessidade de transpilação nas versões estáveis de Chrome, Firefox, Safari e Edge. |
| RNF-10 | Arquitetura | Persistência e Migração Transparente | Abstração ORM via SQLAlchemy permitindo transição transparente entre SQLite (desenvolvimento) e PostgreSQL (produção). Evolução do esquema por migrations versionadas (Alembic), com scripts de upgrade e downgrade que permitam rollback. |
| RNF-11 | Segurança | Validação e Sanitização de Entradas | Validação de tipos, formatos e tamanhos de todos os campos por schemas Pydantic; escape do conteúdo enviado por usuários (ex.: comentários de avaliações) na saída do frontend; consultas exclusivamente parametrizadas via ORM, sem concatenação de SQL, prevenindo SQL Injection e XSS. |
| RNF-12 | Segurança | Política de CORS Restrita | A API aceita requisições apenas das origens listadas em ALLOWED_ORIGINS, sem uso de curinga (*) em produção, com métodos e cabeçalhos explicitamente permitidos. |
| RNF-13 | Segurança | Gestão de Segredos | Segredos (SECRET_KEY, DATABASE_URL, credenciais de e-mail) mantidos somente em variáveis de ambiente, fora do repositório, com valores distintos por ambiente, validação na inicialização e rotação periódica. Dados de demonstração (seed) desabilitados em produção. |
| RNF-14 | Confiabilidade | Registro de Logs e Auditoria | Registro estruturado de eventos de autenticação (sucesso e falha), cancelamentos e ações administrativas, com usuário, ação, entidade, IP e data/hora, sem armazenar senhas ou tokens, e com período de retenção definido. |
| RNF-15 | Confiabilidade | Backup e Retenção de Dados | Backup automático diário do banco de dados, com retenção mínima de 30 dias, armazenamento em local distinto do servidor de aplicação e teste periódico de restauração. |
| RNF-16 | Manutenibilidade | Gestão de Dependências | Versões fixadas em requirements.txt, auditoria periódica de vulnerabilidades (pip-audit) e atualização automatizada de dependências (Dependabot). |
| RNF-17 | Operação | Monitoramento e Observabilidade | Endpoint /health com verificação de conectividade do banco, coleta de métricas básicas (latência e taxa de erros 5xx) e alertas em caso de indisponibilidade. |
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
| Autenticação | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/esqueci-senha`, `POST /auth/redefinir-senha` | Conforme operação |
| Serviços | `GET /services/`, `GET /services/{service_id}` | Público |
| Serviços (gestão) | `POST /services/`, `PUT /services/{service_id}`, `DELETE /services/{service_id}` | Administrador |
| Agendamentos | `GET /appointments/`, `GET /appointments/disponiveis`, `POST /appointments/`, `GET/PUT/DELETE /appointments/{appointment_id}` | Autenticado e/ou dono/equipe |
| Avaliações | `GET /appointments/avaliacoes`, `POST /appointments/{appointment_id}/avaliacao` | Leitura pública; escrita pelo cliente dono |
| Administração | `POST /admin/agendamentos`, `GET /admin/agenda`, `GET /admin/me/agenda`, `GET /admin/relatorio` | Administrador ou barbeiro, conforme rota |
| Moderação | `GET /admin/avaliacoes`, `PATCH /admin/avaliacoes/{avaliacao_id}/ocultar` | Administrador |
| Institucional | `GET /informacoes/`, `POST /informacoes/`, `PUT /informacoes/` | Leitura pública; escrita administrativa |
| Usuários | `GET /users/`, `GET /users/barbeiros`, `GET/PUT /users/{user_id}`, `DELETE /users/me` | Operações administrativas ou próprio usuário |
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
│   ├── database.py             # Engine SQLAlchemy, sessão e atualizações de schema
│   ├── dependencies.py         # Dependência de usuário autenticado
│   ├── booking.py              # Validação de horário, conflito e serialização
│   ├── core/security.py        # Hash de senha e operações JWT
│   ├── models/user.py          # Modelos ORM e enums do domínio
│   ├── schemas/                # Schemas Pydantic de entrada e resposta
│   └── routers/                # Endpoints por domínio
└── requirements.txt

frontend/
├── assets/
│   ├── css/                    # Estilos gerais, home, cliente e painel admin
│   ├── js/                     # API, autenticação, agendamento e gestão
│   └── images/
└── pages/                      # Páginas HTML
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

### Resultado da última validação local

Registro de 2026-10-29: a suíte Python com SQLite temporário executou 185 testes (179 passaram e 6 testes PostgreSQL foram ignorados); os testes Node tiveram 20 aprovações. Playwright teve 51 aprovações; 6 casos não iniciaram porque Firefox e WebKit não estavam instalados. O `pip-audit` não encontrou vulnerabilidades conhecidas. PostgreSQL descartável e CI remota não foram executados nesta rodada. Consulte `docs/REQUISITOS_STATUS.md` para detalhes e pendências; esses resultados não substituem a validação no ambiente de implantação.

## Limitações e cuidados antes de produção

- O token de redefinição não é devolvido pela API nem gravado em logs da aplicação. Configure SMTP também para testar a recuperação localmente; sem entrega confirmada, o token não fica utilizável.
- O endpoint `GET /seed` só existe com `APP_ENV=development`; o processo recusa iniciar se `APP_ENV` estiver ausente ou inválido. A resposta não divulga credenciais.
- O CORS aceita apenas as origens normalizadas listadas em `CORS_ALLOWED_ORIGINS`. Em desenvolvimento, se a variável estiver ausente, é permitida a origem documentada `http://127.0.0.1:5500`. Em produção, a variável é obrigatória e deve conter uma ou mais origens HTTPS exatas do frontend publicado, incluindo a porta não padrão quando aplicável. Não use `*` nem inclua caminhos.
- Novas alterações de schema devem continuar sendo registradas em revisões Alembic e testadas em SQLite e PostgreSQL.
- Consentimento e anonimização implementados são controles técnicos; não substituem avaliação jurídica e operacional de conformidade com a LGPD.

## Homologação no Render

`render.yaml` descreve um Static Site e um Web Service com PostgreSQL independente. O build estático usa Node 22 somente para gerar o arquivo público de configuração da API; o site publicado continua sendo HTML/CSS/JavaScript estático. Configure `PUBLIC_API_URL` no Static Site. No backend, preencha `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `PASSWORD_RESET_URL` e as variáveis SMTP com os domínios e valores do ambiente. O Blueprint não contém credenciais; `SECRET_KEY` é gerada pelo Render e `DATABASE_URL` referencia o banco provisionado.

O comando Alembic está em `preDeployCommand`, disponível no Render apenas para serviços web pagos. O processo de criação do administrador segue manual e interativo com `python -m app.initial_admin`, depois de as migrations terminarem. Consulte [preparação Render](docs/IMPLANTACAO_E_REUTILIZACAO.md#homologacao-render) antes de provisionar. Não configure SMTP de produção em homologação sem credenciais específicas do ambiente.

## Equipe

Projeto desenvolvido por estudantes de DSM da FATEC Itaquera. Consulte o histórico do repositório para autoria por alteração e contribuições.
