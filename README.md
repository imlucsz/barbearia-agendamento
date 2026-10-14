# 💈 Sistema de Agendamento Online - Barbearia

> Projeto acadêmico desenvolvido por estudantes do curso de Desenvolvimento de Software Multiplataforma (DSM) da **FATEC Itaquera**.

O sistema é uma solução web para agendamento online de barbearias e estabelecimentos de estética. A aplicação permite que clientes visualizem o catálogo de serviços, consultem disponibilidade de horários e realizem agendamentos. Além disso, conta com um painel administrativo restrito para gestão de horários, equipe e relatórios operacionais.

---

## 🛠️ Tecnologias Utilizadas

### **Backend**
* **Linguagem:** Python 3.10+
* **Framework:** FastAPI
* **ORM / Banco de Dados:** SQLAlchemy (SQLite por padrão; aceita PostgreSQL via `DATABASE_URL`)
* **Autenticação:** JWT (JSON Web Tokens) + Passlib (Hash de senhas)
* **Documentação:** OpenAPI / Swagger UI (Nativo do FastAPI)

### **Frontend**
* **Estrutura & Estilo:** HTML5, CSS3 (Layout Responsivo)
* **Consumo da API:** JavaScript Vanilla (ES6+) via API `fetch()`

---

## 📌 Requisitos do Sistema

### Requisitos Funcionais (RF01–RF22)

| Código | Requisito |
| :--- | :--- |
| **RF01** | Exibir catálogo de serviços com preço e duração para visitantes. |
| **RF02** | Exibir informações institucionais — endereço, mapa e horário de funcionamento — para visitantes. |
| **RF03** | Exibir a nota média das avaliações para visitantes. |
| **RF04** | Cadastrar conta de cliente. |
| **RF05** | Autenticar clientes, barbeiros e gestores, controlando o acesso por perfil. |
| **RF06** | Permitir recuperação de senha. |
| **RF07** | Consultar horários disponíveis por serviço, profissional e data, conforme RN-01. |
| **RF08** | Agendar um serviço com profissional, data e horário. |
| **RF09** | Cancelar agendamento conforme RN-02. |
| **RF10** | Reagendar agendamento conforme RN-02. |
| **RF11** | Consultar histórico de agendamentos. |
| **RF12** | Avaliar atendimento concluído conforme RN-04. |
| **RF13** | Visualizar agenda do dia: a própria agenda para barbeiros e a agenda de todos para gestores. |
| **RF14** | Marcar atendimento como concluído, cancelado ou falta, registrando o valor cobrado. |
| **RF15** | Criar agendamento manual para atendimento presencial ou por telefone. |
| **RF16** | Gerenciar serviços (CRUD), incluindo preço e duração. |
| **RF17** | Gerenciar barbeiros e os serviços que cada um executa. |
| **RF18** | Gerenciar jornadas, folgas, feriados e bloqueios de horário. |
| **RF19** | Gerenciar clientes: visualizar, editar e bloquear. |
| **RF20** | Gerenciar informações institucionais. |
| **RF21** | Emitir relatório financeiro por período com base nos valores registrados em RF14. |
| **RF22** | Moderar avaliações. |

### Regras de Negócio

| Código | Regra |
| :--- | :--- |
| **RN-01** | Um horário está disponível quando está dentro da jornada do barbeiro, não possui bloqueio ou conflito e comporta a duração do serviço. |
| **RN-02** | Cancelamento e reagendamento exigem pelo menos **24 horas** de antecedência. Cada agendamento pode ser reagendado no máximo **2 vezes**. |
| **RN-03** | Agendamentos podem ser feitos com até **14 dias** de antecedência. |
| **RN-04** | Somente o cliente dono de um agendamento concluído pode avaliá-lo, uma única vez por agendamento. |
| **RN-05** | O agendamento preserva um snapshot do preço e da duração do serviço no momento da criação. |

### Requisitos Não Funcionais

| Código | Requisito |
| :--- | :--- |
| **RNF-01** | Evitar overbooking mesmo com acessos simultâneos, usando restrição de unicidade no banco de dados. |
| **RNF-02** | Armazenar senhas com hash e usar sessões com expiração. |
| **RNF-03** | Oferecer interface responsiva, priorizando o uso em celulares. |
| **RNF-04** | Atender à LGPD, incluindo consentimento e exclusão de conta. |
| **RNF-05** | Impedir acesso a rotas administrativas sem autenticação e perfil adequado. |

---

## 👥 Equipe de Desenvolvimento

### 🐍 **Backend (Python / FastAPI)**
* **Lucas Araújo de Souza:** Arquitetura FastAPI, conexão DB, Autenticação JWT (`RF04`), Painel Admin (`RF07`) e rotas de segurança.
* **Luiz Gustavo dos Santos Almeida:** Modelagem ORM (`SQLAlchemy`), CRUD de Serviços/Barbeiros (`RF01`, `RF08`), Regras de Agendamento (`RF03`, `RF05`) e Avaliações (`RF06`).

### 🌐 **Frontend (HTML / CSS / JavaScript)**
* **Kevin Savimbi Miguel:** Páginas Institucionais (`RF02`), Estilização Global/CSS Base e Seção Visual de Avaliações (`RF06`).
* **Vitor Varischi De Oliveira:** Interface do Catálogo de Serviços (`RF01`) e Telas de Cadastro/Login (`RF04`).
* **Thiago Santos Correia:** Motor Visual de Agendamento (`RF03`), Painel do Cliente (`RF05`), Painel Administrativo (`RF07`, `RF08`) e Integração JS (`fetch`).

---

## 📁 Estrutura do Repositório

```text
barbearia-agendamento/
├── .gitignore
├── README.md
│
├── backend/                        # 🐍 Lucas & Luiz
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # Ponto de entrada do FastAPI
│   │   ├── database.py             # Conexão com o Banco de Dados (SQLAlchemy)
│   │   ├── models/                 # Tabelas do Banco (Luiz)
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── service.py
│   │   │   └── appointment.py
│   │   ├── schemas/                # Schemas Pydantic (Validação)
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   └── appointment.py
│   │   ├── routers/                # Endpoints / Rotas da API
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # Login/JWT (Lucas)
│   │   │   ├── services.py         # CRUD Serviços (Luiz)
│   │   │   ├── appointments.py     # Agendamentos (Luiz)
│   │   │   └── admin.py            # Painel Admin: agenda e financeiro (Lucas)
│   │   └── core/                   # Segurança e utilitários (Lucas)
│   │       ├── security.py
│   │       └── config.py
│   ├── requirements.txt            # Dependências (fastapi, uvicorn, sqlalchemy, etc)
│   └── .env.example                # Exemplo de variáveis de ambiente
│
└── frontend/                       # 🌐 Kevin, Varischi & Thiago
    ├── assets/
    │   ├── css/
    │   │   ├── style.css           # Estilo geral (Kevin)
    │   │   ├── client.css          # Estilos do cliente (Varischi)
    │   │   └── admin.css           # Estilos do painel admin (Thiago)
    │   ├── js/
    │   │   ├── api.js              # Configuração base do fetch (Thiago)
    │   │   ├── auth.js             # Lógica de Login/Token (Thiago)
    │   │   ├── schedule.js         # Lógica de Agendamento (Thiago)
    │   │   ├── agenda_admin.js     # Agenda semanal do painel admin (Thiago)
    │   │   └── financeiro_admin.js # Resumo financeiro do painel admin (Thiago)
    │   └── images/                 # Colocar aqui Logos, banners e fotos
    │       └── icon-user.webp
    ├── pages/
    │   ├── index.html              # Home Institucional + Mapa (Kevin)
    │   ├── catalog.html            # Catálogo de Serviços (Varischi)
    │   ├── login.html              # Login e Cadastro (Varischi)
    │   ├── schedule.html           # Tela de Agendamento (Thiago)
    │   └── admin.html              # Painel Administrativo (Thiago)
    └── README.md
