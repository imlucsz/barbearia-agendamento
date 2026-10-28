# Sistema de Agendamento Online para Barbearia

Projeto acadêmico do curso de Desenvolvimento de Software Multiplataforma (DSM) da FATEC Itaquera. O sistema reúne um site público, fluxo de agendamento para clientes e painel de gestão da barbearia.

## Tecnologias

- **Frontend:** HTML5, CSS3 responsivo e JavaScript ES Modules (Vanilla).
- **Backend:** Python, FastAPI, Pydantic e SQLAlchemy.
- **Banco de dados:** SQLite por padrão; PostgreSQL pode ser usado configurando a URL e instalando o driver correspondente.
- **Autenticação:** JWT Bearer e senha com hash bcrypt.

## Requisitos

- Python 3.10 ou superior (recomendado Python 3.11+).
- Navegador moderno.
- Git, para clonar o repositório.
- Opcional: PostgreSQL instalado e seu driver Python, caso não use SQLite.

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

No ambiente local (`APP_ENV=development`), o banco padrão é `sqlite:///./barbearia.db`, relativo ao diretório `backend`. Nos demais ambientes, `DATABASE_URL` deve ser configurada explicitamente; a API falha ao iniciar se estiver ausente. A aplicação ainda cria tabelas ausentes com `Base.metadata.create_all()` e aplica atualizações aditivas específicas ao iniciar. As mudanças versionadas de schema devem ser aplicadas explicitamente pelo Alembic antes de disponibilizar a nova versão da API.

### Migrações de banco com Alembic

O Alembic usa a mesma variável `DATABASE_URL` da aplicação, carregada do ambiente ou de `backend/.env`. Nenhuma URL com credenciais fica gravada no repositório. Execute os comandos a partir de `backend`, com as dependências do `requirements.txt` instaladas:

```powershell
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic history
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Esta primeira revisão **não é uma migração de criação de schema**: ela só procura e remove a restrição única antiga de `appointments(service_id, data_hora)`. Se a tabela não existir, a revisão não cria tabelas e registra a versão; a inicialização da aplicação continua responsável pela criação do schema novo. Também não há `stamp` automático.

Procedimento de adoção:

- **Banco existente com a restrição antiga:** faça backup, pare a API, confirme que `DATABASE_URL` aponta para esse banco e execute `python -m alembic upgrade head`. A revisão remove somente a restrição cujas colunas são `service_id` e `data_hora`, sem depender do nome. Depois, inicie a API. A validação por intervalo e barbeiro continua no backend.
- **Banco existente sem essa restrição:** execute o mesmo `upgrade head`. A revisão não altera a tabela e registra a versão do Alembic.
- **Banco novo:** pode executar `upgrade head` antes da primeira inicialização (a revisão não cria tabelas) e depois iniciar a API para `create_all()`, ou iniciar a API primeiro e executar a migração em seguida. Em ambos os casos, o modelo atual cria `appointments` sem a unicidade global.
- **Banco com `alembic_version` preexistente ou schema inesperado:** interrompa a adoção e compare o histórico e o schema antes de aplicar ou marcar revisões. Não use `stamp` para contornar divergências sem uma inspeção e backup.

Para reverter a revisão, primeiro pare a API e avalie os dados. `python -m alembic downgrade -1` só recria a unicidade antiga se não houver duas linhas com o mesmo serviço e início. Se houver duplicatas, o downgrade falha claramente e preserva as reservas; resolva os registros de forma explícita e faça backup antes de tentar novamente. Não apague nem altere reservas automaticamente para forçar a reversão.

#### Testes de integração PostgreSQL

Os testes usam SQLite temporário por padrão, mesmo que `BOOKING_TEST_POSTGRES_URL` esteja definida. Para habilitar PostgreSQL, configure **ambas** `BOOKING_TEST_BACKEND=postgresql` e `BOOKING_TEST_POSTGRES_URL` com uma URL `postgresql+psycopg://` cujo nome de banco termine em `_test`. O suporte não usa `DATABASE_URL` nem lê `.env` para escolher o banco de teste. Antes de criar qualquer schema, valida a autenticação e confirma o banco e usuário conectados; depois cria um schema `barbearia_test_*` exclusivo e remove somente esse schema ao terminar. O banco dedicado precisa permitir `CREATE SCHEMA` e `DROP SCHEMA`. Não aponte a URL a bancos de desenvolvimento ou produção.

O projeto fornece `compose.postgres-test.yml` para um PostgreSQL efêmero, ligado somente a `127.0.0.1:55432`, sem volume persistente. A configuração não foi iniciada automaticamente. No PowerShell, depois de instalar manualmente as dependências do `requirements.txt` e ter Docker Compose disponível:

```powershell
$env:POSTGRES_TEST_PASSWORD = (& .\.venv\Scripts\python.exe -c 'import secrets; print(secrets.token_urlsafe(24))')
docker compose -f ..\compose.postgres-test.yml up -d --wait
$env:BOOKING_TEST_POSTGRES_URL = "postgresql+psycopg://barbearia_test:$($env:POSTGRES_TEST_PASSWORD)@127.0.0.1:55432/barbearia_test"
$env:BOOKING_TEST_BACKEND = "postgresql"
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_postgres_booking_migration.py" -v
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
| Administrador | `admin@barbearia.com` | `admin123` |
| Barbeiro | `barbeiro@barbearia.com` | `barbeiro123` |
| Cliente | `cliente@barbearia.com` | `cliente123` |

**Uso exclusivamente local:** `/seed` só é registrado quando `APP_ENV=development` estiver definido explicitamente. Configure essa variável antes de iniciar a API local; sem ela, a rota não fica disponível. A resposta confirma a criação dos dados, mas não retorna credenciais. Não habilite o endpoint em ambientes publicados.

### 3. Servir o frontend

Em outro terminal, na raiz do repositório:

```powershell
python -m http.server 5500
```

Abra `http://127.0.0.1:5500/frontend/pages/index.html`. A API usada pelo frontend é configurada em `frontend/assets/js/api.js`; por padrão, aponta para `http://127.0.0.1:8000`. Se o backend estiver em outro endereço, ajuste `window.BARBEARIA_API_URL` antes dos módulos da página ou altere o valor padrão em `api.js`.

## Variáveis de ambiente

O arquivo `backend/.env.example` contém os valores iniciais. Copie-o para `backend/.env` e ajuste conforme seu ambiente:

| Variável | Finalidade | Padrão local |
| --- | --- | --- |
| `DATABASE_URL` | URL de conexão SQLAlchemy | `sqlite:///./barbearia.db` |
| `CORS_ALLOWED_ORIGINS` | Origens web explicitamente autorizadas, separadas por vírgula | `http://127.0.0.1:5500` em desenvolvimento; obrigatória em produção, com uma ou mais origens HTTPS reais do frontend |
| `SECRET_KEY` | Chave privada de assinatura JWT, com pelo menos 32 bytes UTF-8 | Obrigatória; não há valor padrão |
| `ALGORITHM` | Algoritmo JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Validade do token de acesso em minutos | `1440` (24 horas) |
| `APP_ENV` | Ambiente de execução; `/seed` só é habilitado com o valor explícito `development` | `development` no `backend/.env.example` para uso local; ausente, a rota fica desabilitada |

O envio de redefinição de senha usa SMTP com STARTTLS, configurado por `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` e `PASSWORD_RESET_URL`; o último deve apontar para `frontend/pages/reset.html`. Não há credenciais SMTP fornecidas pelo projeto. Em desenvolvimento explicitamente configurado e sem SMTP, o token fica disponível somente no log local do backend. Fora de desenvolvimento, configuração ausente ou falha de envio não deixa um token utilizável e a API mantém a resposta genérica. Defina `APP_ENV=production` em implantações publicadas; o `.env.example` é para desenvolvimento local.

Gere uma chave uma única vez e guarde-a em `backend/.env` (não gere uma chave nova a cada inicialização):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copie o resultado para `SECRET_KEY` em `backend/.env`. A aplicação falha ao iniciar se a chave estiver ausente, vazia, curta ou parecer um valor de exemplo. O `.env.example` deixa essa variável vazia intencionalmente. Use uma chave persistente e privada por ambiente; não envie `.env` ao Git. Em produção, configure também HTTPS, restrinja CORS e não use as credenciais de demonstração.

Para PostgreSQL, defina `DATABASE_URL` com a URL SQLAlchemy do banco e instale o driver PostgreSQL compatível com essa URL. O `requirements.txt` atual não instala um driver PostgreSQL.

## Funcionalidades e requisitos

### Requisitos funcionais (RF01–RF22)

| Código | Requisito |
| --- | --- |
| **RF01** | Exibir catálogo público de serviços, com preço e duração. |
| **RF02** | Exibir informações institucionais: endereço, mapa e horário de funcionamento. |
| **RF03** | Exibir a nota média das avaliações públicas. |
| **RF04** | Cadastrar conta de cliente. |
| **RF05** | Autenticar clientes, barbeiros e administradores, com controle por perfil. |
| **RF06** | Solicitar redefinição de senha. O envio de e-mail ainda depende de integração com um provedor. |
| **RF07** | Consultar horários por serviço, profissional e data, respeitando RN-01. |
| **RF08** | Agendar serviço, profissional, data e horário. |
| **RF09** | Cancelar agendamento conforme RN-02. |
| **RF10** | Reagendar agendamento conforme RN-02. |
| **RF11** | Consultar histórico de agendamentos do cliente. |
| **RF12** | Avaliar atendimento concluído conforme RN-04. |
| **RF13** | Consultar agenda do dia: barbeiro vê a própria; administrador vê a agenda geral. |
| **RF14** | Registrar atendimento concluído, cancelado ou falta e o valor cobrado ao concluir. |
| **RF15** | Criar agendamento manual, vinculando cliente cadastrado ou informando o nome de cliente avulso. |
| **RF16** | Criar, editar e excluir serviços, com preço e duração. |
| **RF17** | Associar serviços a barbeiros e remover associações. |
| **RF18** | Configurar jornadas, folgas, feriados e bloqueios de horário. |
| **RF19** | Consultar, editar e bloquear/desbloquear clientes. |
| **RF20** | Consultar e gerenciar informações institucionais. |
| **RF21** | Emitir relatório financeiro por período, com base nos atendimentos concluídos/avaliados. |
| **RF22** | Moderar avaliações, ocultando ou reexibindo avaliações. |

### Regras de negócio

| Código | Regra |
| --- | --- |
| **RN-01** | Um horário disponível deve estar dentro da jornada, sem bloqueio ou conflito e comportar a duração do serviço. |
| **RN-02** | Cliente precisa cancelar/reagendar com pelo menos 24 horas de antecedência. Cada agendamento permite até 2 reagendamentos. |
| **RN-03** | Agendamentos podem ser feitos com até 14 dias de antecedência. |
| **RN-04** | Apenas o dono de um agendamento concluído pode avaliá-lo, uma única vez. |
| **RN-05** | O agendamento mantém snapshot de preço e duração do serviço no momento da criação. |

### Requisitos não funcionais

| Código | Requisito |
| --- | --- |
| **RNF-01** | Serializar reservas e reagendamentos por barbeiro antes de verificar conflitos. |
| **RNF-02** | Senhas com hash bcrypt e tokens JWT com expiração configurável. |
| **RNF-03** | Interface responsiva, priorizando dispositivos móveis. |
| **RNF-04** | Registrar consentimento no cadastro e permitir desativação/anônimização da conta. A adequação legal deve ser revisada para o contexto real. |
| **RNF-05** | Restringir operações administrativas a usuários autenticados e perfis autorizados. |

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
| Saúde | `GET /`, `GET /health` | Público |
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

## Limitações e cuidados antes de produção

- O token de redefinição nunca é devolvido pela API. Em desenvolvimento explicitamente configurado, sem SMTP, ele aparece somente no log local; em outros ambientes, configure a entrega SMTP descrita acima.
- O endpoint `GET /seed` só existe com `APP_ENV=development`; sem essa configuração explícita, inclusive quando `APP_ENV` está ausente, a rota não é registrada. A resposta não divulga credenciais.
- O CORS aceita apenas as origens normalizadas listadas em `CORS_ALLOWED_ORIGINS`. Em desenvolvimento, se a variável estiver ausente, é permitida a origem documentada `http://127.0.0.1:5500`. Em produção, a variável é obrigatória e deve conter uma ou mais origens HTTPS exatas do frontend publicado, incluindo a porta não padrão quando aplicável. Não use `*` nem inclua caminhos.
- A atualização de schema em `database.py` cobre colunas específicas, mas não substitui migrações versionadas para evolução contínua do banco.
- Consentimento e anonimização implementados são controles técnicos; não substituem avaliação jurídica e operacional de conformidade com a LGPD.

## Equipe

Projeto desenvolvido por estudantes de DSM da FATEC Itaquera. Consulte o histórico do repositório para autoria por alteração e contribuições.
