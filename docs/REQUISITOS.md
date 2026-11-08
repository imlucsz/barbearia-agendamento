# Requisitos do sistema (fonte de verdade para o Codex)

Extraído do documento SAAS_BARBEARIA (FATEC Itaquera, 2026): 24 requisitos funcionais, 18 não funcionais e 5 regras de negócio.
Cada instalação atende uma barbearia, com domínio, banco e configuração próprios; não há multi-tenancy.
O status de implementação fica em docs/REQUISITOS_STATUS.md, não neste arquivo.

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
| RF13 | Consulta de Agenda | Exibir agenda diária: o barbeiro visualiza a sua própria e o admin visualiza a geral. | Barbeiro / Admin |
| RF14 | Registro de Atendimento | Registrar status do agendamento (Concluído, Cancelado, Falta) e o valor final cobrado. | Barbeiro / Admin |
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
