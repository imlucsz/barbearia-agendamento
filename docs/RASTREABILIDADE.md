# Rastreabilidade entre requisitos e implementação

Validação formal local de 2026-11-01 para v1.0.0-rc.1. Candidato: working tree sobre `main` / `218575f202e897a92f23cd4ee23091c2b1438045`, incluindo correções anteriores não commitadas de auditoria/backup. A identificação do recorte validado e os limites de aprovação estão em `REQUISITOS_STATUS.md`. Implementado indica cobertura técnica; Parcial e A validar preservam as dependências externas.

## Tabela 4 — Situação dos requisitos funcionais

Formato sugerido para transcrição ao trabalho. `docs/REQUISITOS.md` contém apenas as Tabelas 1, 2 e 3; portanto, os números 4 e 6 abaixo são adotados para as tabelas de situação solicitadas, sem afirmar que sejam a numeração do documento acadêmico original.

| Requisito | Situação |
|---|---|
| RF01 | Implementado |
| RF02 | Implementado |
| RF03 | Implementado |
| RF04 | Implementado |
| RF05 | Implementado |
| RF06 | A validar |
| RF07 | Implementado |
| RF08 | Implementado |
| RF09 | Implementado |
| RF10 | Implementado |
| RF11 | Implementado |
| RF12 | Implementado |
| RF13 | Implementado |
| RF14 | Implementado |
| RF15 | Implementado |
| RF16 | Implementado |
| RF17 | Implementado |
| RF18 | Implementado |
| RF19 | Implementado |
| RF20 | Implementado |
| RF21 | Implementado |
| RF22 | Implementado |
| RF23 | Implementado |
| RF24 | Implementado |

## Tabela 6 — Situação dos requisitos não funcionais

| Requisito | Situação |
|---|---|
| RNF-01 | Implementado |
| RNF-02 | Implementado |
| RNF-03 | Implementado |
| RNF-04 | Implementado |
| RNF-05 | Implementado |
| RNF-06 | Parcial |
| RNF-07 | Implementado |
| RNF-08 | Implementado |
| RNF-09 | Parcial |
| RNF-10 | Implementado |
| RNF-11 | Implementado |
| RNF-12 | Implementado |
| RNF-13 | Parcial |
| RNF-14 | Implementado |
| RNF-15 | Parcial |
| RNF-16 | Implementado |
| RNF-17 | Parcial |
| RNF-18 | Parcial |

## Matriz detalhada: requisito, classes/módulos, rotas e testes

### Requisitos funcionais

| Req. | Classes/módulos e rotas | Testes de rastreio |
|---|---|---|
| RF01 | `Service`; `routers/services.py`, `GET /services/`; home e seleção de serviço | `test_public_catalog.py`; `test_schema_validation.py`; Playwright catálogo público |
| RF02 | `routers/institucional.py`, rotas GET/POST/PUT de informações; `home.js`, `admin_management.js` | `test_institutional_info.py`; Playwright painel/informações institucionais |
| RF03 | `routers/appointments.py`, `GET /appointments/avaliacoes`; `home.js:loadReviews` | `test_public_reviews.py`; Playwright média com ocultas e sem avaliações |
| RF04 | `ConsentimentoLGPD`, `User`; `POST /auth/register` | `test_auth_sessions.py:test_registration_records_versioned_consent_and_login_issues_hashed_cookie_token` |
| RF05 | `core/security.py`, `dependencies.py`; `POST /auth/login`, `/auth/refresh`, `/auth/logout` | `test_auth_sessions.py`; `test_authentication_regression.py`; E2E cadastro/login/refresh/logout |
| RF06 | `PasswordResetToken`; `POST /auth/esqueci-senha`, `/auth/redefinir-senha`; `core/email.py` (Brevo HTTPS/SMTP) | `test_password_reset.py`, `test_brevo_email.py`, configuração/fragmento; suítes RC aprovadas. Entrega e reset reais no ambiente publicado ainda A validar com conta própria |
| RF07 | `booking.py`; `GET /appointments/disponiveis` | `test_booking_temporal.py` (filtros, perfil, jornada e janela); Playwright disponibilidade |
| RF08 | `Appointment`, `booking.py`; `POST /appointments/` | `test_booking_integrity.py`, `test_booking_temporal.py`; E2E reserva e conflito concorrente |
| RF09 | `Appointment`; `PATCH /appointments/{id}` e cancelamento | `test_booking_temporal.py:test_cancel_requires_exactly_twenty_four_hours_or_more`; `test_authorization.py`; E2E cancelamento |
| RF10 | `Appointment`; `PATCH /appointments/{id}` | `test_booking_temporal.py:test_reschedule_obeys_exact_twenty_four_hour_limit_and_two_change_cap`; `test_booking_integrity.py`; E2E reagendamento |
| RF11 | `routers/appointments.py:get_user_appointments`; tela `schedule.js` | `test_authorization.py:test_client_history_includes_past_and_future_records_beyond_default_page`; E2E histórico completo |
| RF12 | `Avaliacao`; `POST /appointments/{id}/avaliacao` | `test_appointment_reviews.py`; E2E histórico e envio de avaliação |
| RF13 | `routers/admin.py:get_agenda_by_date/get_my_agenda_by_date`; agenda do admin/barbeiro | `test_authorization.py` (data, limites, perfil e propriedade); E2E dedicado RF13 desktop/mobile aprovado na RC |
| RF14 | `booking.py:validate_appointment_status_transition`; `appointments.py:update_appointment`; `agenda_admin.js` | `test_rf14_service_record.py`, `test_appointment_reviews.py`; matriz normativa implementada, tempo/perfil/valor/auditoria; SQLite/PostgreSQL/E2E RC aprovados |
| RF15 | `routers/admin.py:create_manual_appointment`; `POST /admin/agendamentos`; `booking.py` | `test_authorization.py:test_barber_cannot_execute_admin_only_operations`; `test_booking_temporal.py:test_public_and_admin_creation_keep_price_and_duration_snapshots`; E2E de operação administrativa |
| RF16 | `Service`; CRUD `routers/services.py` | `test_services_crud.py`, `test_schema_validation.py`; E2E CRUD de serviços |
| RF17 | `BarbeiroServico`; `routers/barbeiro_servico.py` | `test_barber_service_assignments.py`; E2E associação/remoção no painel |
| RF18 | `HorarioTrabalho`, `BloqueioAgenda`; `routers/horario.py` | `test_schedule_block_lifecycle.py`, `test_authorization.py`; E2E CRUD de jornadas/bloqueios |
| RF19 | `User`; `routers/users.py`; tela `admin_management.js` | `test_auth_sessions.py:test_blocking_client_revokes_refresh_tokens`; Node `session.test.mjs`; E2E bloqueio/desbloqueio imediato |
| RF20 | modelo institucional; `routers/institucional.py`; `home.js`, painel admin | `test_institutional_info.py`; Playwright edição/leitura institucional |
| RF21 | `routers/admin.py:get_financial_report`; `/admin/relatorio/financeiro`, `/admin/relatorio/csv`; `financeiro_admin.js` | `test_financial_report.py`; E2E filtro, tabela e CSV |
| RF22 | `Avaliacao`; rotas administrativas de moderação; avaliações públicas | `test_review_moderation.py`; E2E moderação e home |
| RF23 | `AuditLog`, `core/audit.py`; `GET /admin/auditoria`; painel admin | `test_audit.py`, `test_audit_catalog.py`; matriz em `AUDITORIA_RF23_RNF14.md`: catálogo exigido, metadados, filtros combinados, período e paginação; PostgreSQL 16 descartável aprovado |
| RF24 | `routers/users.py`; `GET /users/me/exportacao`; `schedule.js`/`client-account.html` | `test_lgpd_portability.py:test_export_is_versioned_complete_and_never_includes_another_user_or_secrets`; E2E download |

### Regras de negócio

| Req. | Classes/módulos e rotas | Testes de rastreio |
|---|---|---|
| RN-01 | `booking.py:validate_booking_slot/lock_barber_for_booking`; reserva, reagendamento e disponibilidade | `test_booking_integrity.py`, `test_booking_temporal.py`; equivalência de slots e consultas limitadas |
| RN-02 | `Appointment`; `routers/appointments.py` | `test_booking_temporal.py` (24 horas e até dois reagendamentos); E2E cancelamento/reagendamento |
| RN-03 | `booking.py:BOOKING_WINDOW_DAYS`; reserva/disponibilidade | `test_booking_temporal.py:test_booking_rejects_past_and_enforces_exact_fourteen_day_instant_boundary` |
| RN-04 | `Avaliacao`; `POST /appointments/{id}/avaliacao` | `test_appointment_reviews.py:test_owner_can_rate_concluded_appointment_only_once` |
| RN-05 | `Appointment.preco/duracao_minutos`; criação pública e manual | `test_booking_temporal.py:test_public_and_admin_creation_keep_price_and_duration_snapshots` |

### Requisitos não funcionais

| Req. | Classes/módulos e rotas | Testes de rastreio |
|---|---|---|
| RNF-01 | `booking.py:lock_barber_for_booking`; reserva/reagendamento | `test_booking_integrity.py:test_concurrent_overlapping_bookings_for_same_barber_only_one_persists`; aprovado SQLite e PostgreSQL 16 descartável nesta RC |
| RNF-02 | `core/security.py`, `RefreshToken`; login/refresh/logout | `test_auth_sessions.py`, `test_configuration.py`, `test_authentication_regression.py`; E2E sessão; Argon2 atual/bcrypt legado: redação normativa antiga a alinhar |
| RNF-03 | CSS responsivo e `responsive-a11y.spec.mjs`; páginas pública/cliente/admin | Três viewports 320×568/390×844/1280×800 nos três motores Playwright aprovadas entre completa e repetição; fluxos desktop/mobile aprovados |
| RNF-04 | `ConsentimentoLGPD`, `users.py`; cadastro, `DELETE /users/me`, `GET /users/me/exportacao` | `test_auth_sessions.py`, `test_lgpd_portability.py`; E2E exportação/exclusão |
| RNF-05 | `dependencies.py:require_roles/ensure_resource_owner`; rotas privadas FastAPI | `test_route_authorization_matrix.py`, `test_authorization.py` |
| RNF-06 | `SecurityHeadersMiddleware`, HTTPS; API e host estático | `test_security_controls.py` aprovado; TLS/redirect/headers publicados não medidos nesta RC. Render saudável é contexto fornecido pelo usuário |
| RNF-07 | `AuthRateLimitMiddleware`, `LoginAttempt`; rotas de autenticação | `test_security_controls.py` (bloqueio, reset, expiração, IPs) |
| RNF-08 | `appointments.py:get_available_slots`, `booking.py:validate_slot_against_loaded_data` | `test_booking_temporal.py:test_availability_matches_legacy_slot_validation_and_uses_bounded_queries`; benchmark SQLite em `BENCH_DISPONIVEIS.md` |
| RNF-09 | JavaScript ES Modules; matriz de projetos Playwright | 63 casos distintos aprovados: completa 60/63 (exit 1, Firefox crash pré-página), repetição Firefox 3/3 fora da sandbox (exit 0); smoke de Chrome/Safari/Edge de marca ainda pendente |
| RNF-10 | SQLAlchemy, `database.py`, Alembic, `render_start.py` | `test_schema_migrations.py`, `test_postgres_booking_migration.py`, `test_render_start.py`; vazio/anterior/head, falha, preservação e paridade SQLite/PostgreSQL RC. Downgrade destrutivo deliberadamente recusado |
| RNF-11 | Schemas Pydantic, `escape-html.mjs`, renderização de mapa/admin | `test_schema_validation.py`, `test_appointment_reviews.py`; Node escape helper; Playwright XSS |
| RNF-12 | `parse_cors_origins`, `CORSMiddleware`; `CORS_ALLOWED_ORIGINS` | `test_application_configuration.py:test_preflight_rejects_unlisted_origin_method_and_header`; nome antigo ALLOWED_ORIGINS na especificação precisa alinhamento |
| RNF-13 | `config.py`, `.env.example`, procedimentos por instalação | Testes de configuração; rotação recorrente é operação externa, sem execução comprovada |
| RNF-14 | `AuditLog`, `core/audit.py`, manutenção de retenção | `test_audit.py`, `test_audit_catalog.py`: atores/IP/UTC, sanitização, falha best-effort, retenção dry-run/expurgo real e limite exato; não comprova agendamento ou coleta externa |
| RNF-15 | Scripts `tools/backup`, plano de recuperação | RC: 4 unitários e ciclo PostgreSQL 16/pg_dump/age/rsync/pg_restore aprovados; head/14 contagens/dados preservados, corrupção rejeitada. Job diário, destino físico externo e retenção real pendentes |
| RNF-16 | `requirements.txt`, Dependabot e workflow CI | RC: pip-audit com resolução completa, 36 dependências, 0 vulnerabilidades; npm audit 0; CI remota deste working tree não executada |
| RNF-17 | `observability.py`, health/readiness e métricas | `test_readiness.py` + `test_observability.py`: 9 aprovados em 2026-11-01; monitor e recebimento de alertas externos ainda não comprovados |
| RNF-18 | Plano de recuperação, scripts backup/restauração | RC: restore mínimo PostgreSQL 16 em 3,339 s, ciclo 3,83 s; não comprova RTO/RPO integral. Responsáveis e ensaio representativo pendentes |

## Resultados da validação formal — 2026-11-01

- SQLite: 266 executados, 259 aprovados, 7 skips de dialeto; PostgreSQL 16 descartável: 266 executados, 264 aprovados, 2 skips exclusivos SQLite; 0 falhas/erros.
- Cobertura backend: migrações vazio/anterior/head, paridade, integridade/double booking, autenticação/RBAC, recuperação local, LGPD, auditoria, RF13/RF14 e startup/readiness.
- Node: 26 aprovados. Backup: 4 unitários e ciclo real descartável de backup/cópia/restore aprovados; nenhuma base real acessada.
- Playwright: completa saiu 1 (60 aprovados/3 Firefox crash antes da página); repetição apenas Firefox fora da sandbox saiu 0 (3/3). Total: 63 casos distintos aprovados, sem alterações de assertions ou aplicação.
- pip-audit: resolução completa, 36 dependências, 0 vulnerabilidades; npm audit: 0 em todas severidades. Rede liberada necessária para ambas; dependências preservadas.
- YAML Render Free: `startCommand` aponta para `python -m app.render_start`, migração/verificação antes da fronteira Uvicorn; health check `/ready`. Sem deploy ou acesso ao serviço nesta rodada.
- RF: 23 Implementados, 1 A validar (RF06), 0 Parciais; RN: 5 Implementadas; RNF: 12 Implementados, 6 Parciais. Parecer: **APROVADA COM RESSALVAS para UAT controlado**; pendências externas de dados reais em `CHECKLIST_PRODUCAO.md`.
- Nenhum P0/P1 de código demonstrado, nenhuma correção de código nesta rodada. Sem nova feature ou repetição de suítes após documentação.
- Não há documento acadêmico original com Tabelas 4 e 6 no repositório; a numeração acima é apresentação proposta das tabelas de situação.

## Histórico útil

Na auditoria de 2026-10-29, a suíte tinha 185 testes, Node 20 e Playwright 51 aprovados/6 sem binários; PostgreSQL local estava indisponível. Esses limites foram superados nas rodadas seguintes e não descrevem o candidato atual. RF13/RF14 já tinham sido concluídos; a marcação antiga Parcial nesta matriz era documental. As correções locais RF23/RNF-14 e backup anteriores foram preservadas e incluídas na validação RC. Histórico detalhado em `REQUISITOS_STATUS.md` e `HISTORICO_FECHAMENTO_BETA_RC1.md`.
