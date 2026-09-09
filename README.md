# 💈 Sistema de Agendamento Online - Barbearia

> Projeto acadêmico desenvolvido por estudantes do curso de Desenvolvimento de Software Multiplataforma (DSM) da **FATEC Itaquera**.

O sistema é uma solução web para agendamento online de barbearias e estabelecimentos de estética. A aplicação permite que clientes visualizem o catálogo de serviços, consultem disponibilidade de horários e realizem agendamentos. Além disso, conta com um painel administrativo restrito para gestão de horários, equipe e relatórios operacionais.

---

## 🛠️ Tecnologias Utilizadas

### **Backend**
* **Linguagem:** Python 3.10+
* **Framework:** FastAPI
* **ORM / Banco de Dados:** SQLAlchemy / SQLite
* **Autenticação:** JWT (JSON Web Tokens) + Passlib (Hash de senhas)
* **Documentação:** OpenAPI / Swagger UI (Nativo do FastAPI)

### **Frontend**
* **Estrutura & Estilo:** HTML5, CSS3 (Layout Responsivo)
* **Consumo da API:** JavaScript Vanilla (ES6+) via API `fetch()`

---

## 📌 Requisitos Funcionais

| Código | Requisito | Descrição |
| :--- | :--- | :--- |
| **RF01** | Catálogo de Serviços | Exibição do menu de serviços com preços e duração estimada. |
| **RF02** | Informações Institucionais | Exibição de endereço, mapa interativo e horários de funcionamento. |
| **RF03** | Agendamento Online | Seleção de serviço, profissional, data e horário disponível. |
| **RF04** | Gestão de Conta do Cliente | Cadastro, login com autenticação e perfil do cliente. |
| **RF05** | Gestão de Agendamentos | Histórico de agendamentos, cancelamento e reagendamento. |
| **RF06** | Avaliações | Cadastro de notas/opiniões com cálculo de média exibido no site. |
| **RF07** | Painel Administrativo | Dashboard do gestor com agenda diária e relatórios financeiros simples. |
| **RF08** | Gestão de Serviços e Equipe | CRUD de serviços, preços, profissionais e jornadas de trabalho. |

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
│   │   │   └── admin.py            # Painel Admin (Lucas)
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
    │   │   └── schedule.js         # Lógica de Agendamento (Thiago)
    │   └── images/                 # Colocar aqui Logos, banners e fotos
    │       └── icon-user.webp
    ├── pages/
    │   ├── index.html              # Home Institucional + Mapa (Kevin)
    │   ├── catalog.html            # Catálogo de Serviços (Varischi)
    │   ├── login.html              # Login e Cadastro (Varischi)
    │   ├── schedule.html           # Tela de Agendamento (Thiago)
    │   └── admin.html              # Painel Administrativo (Thiago)
    └── README.md
