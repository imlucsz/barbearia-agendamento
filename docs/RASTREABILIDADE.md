# Rastreabilidade entre requisitos e implementação

Auditoria local de 2026-10-29. A coluna de testes identifica cobertura existente; os resultados da execução completa constam ao final e em `REQUISITOS_STATUS.md`. Uma situação “Implementado” exige teste correspondente. “Parcial” e “A validar” descrevem escopo não coberto ou dependente de infraestrutura externa.

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
| RF13 | Parcial |
| RF14 | Parcial |
| RF15 | Implementado |
| RF16 | Implementado |
| RF17 | Implementado |
| RF18 | Implementado |
| RF19 | Implementado |
| RF20 | Implementado |
| RF21 | Implementado |
| RF22 | Implementado |
| RF23 | Parcial |
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
| RNF-14 | Parcial |
| RNF-15 | Parcial |
| RNF-16 | Parcial |
| RNF-17 | Implementado |
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
| RF06 | `PasswordResetToken`; `POST /auth/esqueci-senha`, `/auth/redefinir-senha`; `core/email.py` | `test_password_reset.py`; teste real de entrega SMTP não executado (sem SMTP de homologação) |
| RF07 | `booking.py`; `GET /appointments/disponiveis` | `test_booking_temporal.py` (filtros, perfil, jornada e janela); Playwright disponibilidade |
| RF08 | `Appointment`, `booking.py`; `POST /appointments/` | `test_booking_integrity.py`, `test_booking_temporal.py`; E2E reserva e conflito concorrente |
| RF09 | `Appointment`; `PATCH /appointments/{id}` e cancelamento | `test_booking_temporal.py:test_cancel_requires_exactly_twenty_four_hours_or_more`; `test_authorization.py`; E2E cancelamento |
| RF10 | `Appointment`; `PATCH /appointments/{id}` | `test_booking_temporal.py:test_reschedule_obeys_exact_twenty_four_hour_limit_and_two_change_cap`; `test_booking_integrity.py`; E2E reagendamento |
| RF11 | `routers/appointments.py:get_user_appointments`; tela `schedule.js` | `test_authorization.py:test_client_history_includes_past_and_future_records_beyond_default_page`; E2E histórico completo |
| RF12 | `Avaliacao`; `POST /appointments/{id}/avaliacao` | `test_appointment_reviews.py`; E2E histórico e envio de avaliação |
| RF13 | `routers/admin.py:get_agenda_by_date/get_my_agenda_by_date`; agenda do admin/barbeiro | `test_authorization.py:test_barber_sees_only_own_agenda_and_cannot_access_full_or_other_agenda`; falta E2E dedicado à visão diária |
| RF14 | `routers/appointments.py:update_appointment`; tela `agenda_admin.js` | `test_rf14_service_record.py`; E2E registra status e valor; falta matriz normativa de transições entre estados |
| RF15 | `routers/admin.py:create_manual_appointment`; `POST /admin/agendamentos`; `booking.py` | `test_authorization.py:test_barber_cannot_execute_admin_only_operations`; `test_booking_temporal.py:test_public_and_admin_creation_keep_price_and_duration_snapshots`; E2E de operação administrativa |
| RF16 | `Service`; CRUD `routers/services.py` | `test_services_crud.py`, `test_schema_validation.py`; E2E CRUD de serviços |
| RF17 | `BarbeiroServico`; `routers/barbeiro_servico.py` | `test_barber_service_assignments.py`; E2E associação/remoção no painel |
| RF18 | `HorarioTrabalho`, `BloqueioAgenda`; `routers/horario.py` | `test_schedule_block_lifecycle.py`, `test_authorization.py`; E2E CRUD de jornadas/bloqueios |
| RF19 | `User`; `routers/users.py`; tela `admin_management.js` | `test_auth_sessions.py:test_blocking_client_revokes_refresh_tokens`; Node `session.test.mjs`; E2E bloqueio/desbloqueio imediato |
| RF20 | modelo institucional; `routers/institucional.py`; `home.js`, painel admin | `test_institutional_info.py`; Playwright edição/leitura institucional |
| RF21 | `routers/admin.py:get_financial_report`; `/admin/relatorio/financeiro`, `/admin/relatorio/csv`; `financeiro_admin.js` | `test_financial_report.py`; E2E filtro, tabela e CSV |
| RF22 | `Avaliacao`; rotas administrativas de moderação; avaliações públicas | `test_review_moderation.py`; E2E moderação e home |
| RF23 | `AuditLog`, `core/audit.py`; `GET /admin/auditoria`; painel admin | `test_audit.py` (consulta, filtros, paginação, falha/segredos e parte dos eventos); lacuna de teste individual para todos eventos exigidos |
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
| RNF-01 | `booking.py:lock_barber_for_booking`; reserva/reagendamento | `test_booking_integrity.py:test_concurrent_overlapping_bookings_for_same_barber_only_one_persists` (SQLite); PostgreSQL não executado |
| RNF-02 | `core/security.py`, `RefreshToken`; login/refresh/logout | `test_auth_sessions.py`, `test_configuration.py`, `test_authentication_regression.py`; E2E sessão expirada |
| RNF-03 | CSS responsivo e `responsive-a11y.spec.mjs`; páginas pública/cliente/admin | Playwright Chromium nas três viewports; testes E2E essenciais desktop/mobile passaram |
| RNF-04 | `ConsentimentoLGPD`, `users.py`; cadastro, `DELETE /users/me`, `GET /users/me/exportacao` | `test_auth_sessions.py`, `test_lgpd_portability.py`; E2E exportação/exclusão |
| RNF-05 | `dependencies.py:require_roles/ensure_resource_owner`; rotas privadas FastAPI | `test_route_authorization_matrix.py`, `test_authorization.py` |
| RNF-06 | `SecurityHeadersMiddleware`, CORS/HTTPS; API e host estático | `test_security_controls.py`; TLS e headers do host estático dependem de deploy, ainda inexistente |
| RNF-07 | `AuthRateLimitMiddleware`, `LoginAttempt`; rotas de autenticação | `test_security_controls.py` (bloqueio, reset, expiração, IPs) |
| RNF-08 | `appointments.py:get_available_slots`, `booking.py:validate_slot_against_loaded_data` | `test_booking_temporal.py:test_availability_matches_legacy_slot_validation_and_uses_bounded_queries`; benchmark SQLite em `BENCH_DISPONIVEIS.md` |
| RNF-09 | JavaScript ES Modules; matriz de projetos Playwright | 51 testes passaram; Firefox/WebKit falharam ao iniciar porque binários não instalados; ver resultado em `REQUISITOS_STATUS.md` |
| RNF-10 | SQLAlchemy, `database.py`, migrations Alembic | `test_schema_migrations.py`, testes de migração; SQLite passou, PostgreSQL indisponível |
| RNF-11 | Schemas Pydantic, `escape-html.mjs`, renderização de mapa/admin | `test_schema_validation.py`, `test_appointment_reviews.py`; Node escape helper; Playwright XSS |
| RNF-12 | `parse_cors_origins`, `CORSMiddleware`; rotas API | `test_application_configuration.py:test_preflight_rejects_unlisted_origin_method_and_header` |
| RNF-13 | `config.py`, `.env.example`, procedimentos por instalação | Testes de configuração; rotação recorrente é operação externa, sem execução comprovada |
| RNF-14 | `AuditLog`, `core/audit.py`, manutenção de retenção | `test_audit.py`; cobertura ainda não individualiza todo o catálogo de eventos |
| RNF-15 | scripts `tools/backup`, plano de recuperação | Sem teste PostgreSQL local: não há URL de teste nem Docker; restauração deve ser ensaiada em DB descartável |
| RNF-16 | `requirements.txt`, Dependabot e workflow CI | `pip-audit` sem vulnerabilidades; workflow/npm audit não executados nesta rodada |
| RNF-17 | `observability.py`, health/readiness e métricas | `test_readiness.py`, `test_observability.py`, `test_configuration.py` |
| RNF-18 | plano de recuperação, scripts backup/restauração | Documentação presente; exercício cronometrado, responsáveis e resultado de restore pendentes |

## Resultados da rodada

- Python/SQLite: 185 executados; 179 passaram e 6 testes condicionados a PostgreSQL foram ignorados.
- Node: 20 passaram.
- Playwright: 51 passaram; 6 não iniciaram por falta dos binários Firefox/WebKit.
- PostgreSQL descartável: não executado (sem URL explicitamente configurada e sem Docker).
- `pip-audit`: nenhuma vulnerabilidade conhecida; foi necessário executar sem atualização de pip e sem resolução de dependências devido a limitação inicial de rede.
- Não há no repositório o documento acadêmico original com Tabelas 4 e 6. Os nomes acima são uma apresentação proposta, baseada nas 24 RF e 18 RNF de `REQUISITOS.md`.
