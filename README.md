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

O banco padrão é `sqlite:///./barbearia.db`, relativo ao diretório `backend`. Na primeira inicialização, as tabelas são criadas automaticamente. `Base.metadata.create_all()` cria tabelas novas, mas não substitui um sistema de migrações para mudanças complexas de schema.

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

**Uso exclusivamente local:** `/seed` usa credenciais conhecidas e não deve ficar acessível em produção. Troque/remova esse mecanismo e as credenciais antes de publicar a API.

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
| `SECRET_KEY` | Chave de assinatura JWT | Chave de desenvolvimento insegura |
| `ALGORITHM` | Algoritmo JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Validade do token de acesso em minutos | `1440` (24 horas) |
| `APP_ENV` | Ambiente de execução | `development` |

Em produção, defina uma `SECRET_KEY` aleatória e privada, configure HTTPS, restringa CORS e nunca use as credenciais de demonstração. Não envie o arquivo `.env` ao Git.

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

## Testes e validações

Não há atualmente uma suíte automatizada de integração (`test_integration.py` ou `test_integration_final.py`) no repositório. Para validar manualmente a API, use `http://127.0.0.1:8000/docs` e os dados de demonstração. Antes de produção, crie testes automatizados para regras de horário, concorrência, autorização por perfil, redefinição de senha e migrações.

## Limitações e cuidados antes de produção

- O token de redefinição só é devolvido como `dev_token` quando `APP_ENV=development`; configure um provedor de e-mail para entregar o link em produção.
- O endpoint `GET /seed` contém contas e senhas públicas de demonstração e deve ser removido ou protegido no ambiente publicado.
- O CORS atualmente aceita qualquer origem; restrinja `allow_origins` antes de publicar.
- A atualização de schema em `database.py` cobre colunas específicas, mas não substitui migrações versionadas para evolução contínua do banco.
- Consentimento e anonimização implementados são controles técnicos; não substituem avaliação jurídica e operacional de conformidade com a LGPD.

## Equipe

Projeto desenvolvido por estudantes de DSM da FATEC Itaquera. Consulte o histórico do repositório para autoria por alteração e contribuições.
