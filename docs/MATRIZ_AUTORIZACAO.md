# Matriz de autorização

Esta matriz reflete os métodos e caminhos registrados pela API. “Próprio” significa que a rota consulta ou altera somente o recurso do usuário autenticado. Rotas públicas constam explicitamente em `backend/tests/test_route_authorization_matrix.py`; as demais devem declarar `get_current_user` ou uma dependência `require_roles`.

| Método e rota | Público | Cliente | Barbeiro | Admin |
|---|---:|---:|---:|---:|
| `GET/HEAD /openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc` | Sim | Sim | Sim | Sim |
| `GET /`, `GET /health`, `GET /ready` | Sim | Sim | Sim | Sim |
| `GET /metrics` | Token METRICS_TOKEN | — | — | — |
| `POST /auth/register` | Sim | — | — | — |
| `POST /auth/login` | Sim | — | — | — |
| `POST /auth/refresh` | Sim* | — | — | — |
| `POST /auth/logout` | Sim* | — | — | — |
| `POST /auth/esqueci-senha` | Sim | — | — | — |
| `POST /auth/redefinir-senha` | Sim | — | — | — |
| `GET /auth/me` | — | Autenticado | Autenticado | Autenticado |
| `GET /services/` | Sim | Sim | Sim | Sim |
| `GET /services/{service_id}` | Sim | Sim | Sim | Sim |
| `POST /services/` | — | — | — | Sim |
| `PUT /services/{service_id}` | — | — | — | Sim |
| `DELETE /services/{service_id}` | — | — | — | Sim |
| `POST /appointments/` | — | Sim | — | — |
| `GET /appointments/` | — | Próprios | — | Autenticado, consulta os próprios |
| `GET /appointments/disponiveis` | — | Autenticado | Autenticado | Autenticado |
| `GET /appointments/avaliacoes` | Sim | Sim | Sim | Sim |
| `GET /appointments/{appointment_id}` | — | Cliente dono | Barbeiro atribuído | Sim |
| `PUT /appointments/{appointment_id}` | — | Dono: cancelar/reagendar | Barbeiro atribuído: operação da equipe | Sim |
| `DELETE /appointments/{appointment_id}` | — | Próprio | Barbeiro atribuído | Sim |
| `POST /appointments/{appointment_id}/avaliacao` | — | Dono do agendamento | — | — |
| `POST /admin/agendamentos` | — | — | Sim, sempre para si | Sim |
| `GET /admin/agenda` | — | — | — | Sim, agenda completa |
| `GET /admin/me/agenda` | — | — | Própria | Consulta o próprio ID |
| `GET /admin/avaliacoes` | — | — | — | Sim |
| `PATCH /admin/avaliacoes/{avaliacao_id}/ocultar` | — | — | — | Sim |
| `GET /admin/relatorio` | — | — | — | Sim |
| `GET /informacoes/` | Sim | Sim | Sim | Sim |
| `POST /informacoes/` | — | — | — | Sim |
| `PUT /informacoes/` | — | — | — | Sim |
| `GET /users/` | — | — | — | Sim |
| `GET /users/barbeiros` | — | — | — | Sim |
| `GET /users/{user_id}` | — | — | — | Sim, somente cliente |
| `PUT /users/{user_id}` | — | — | — | Sim, somente cliente |
| `DELETE /users/me` | — | Própria conta | Própria conta | Própria conta |
| `GET /horario/jornadas/{barbeiro_id}` | — | — | Próprias | Sim |
| `POST /horario/jornadas` | — | — | Somente para si | Sim |
| `PUT /horario/jornadas/{jornada_id}` | — | — | Própria | Sim |
| `GET /horario/bloqueios/{barbeiro_id}` | — | — | Próprios | Sim |
| `POST /horario/bloqueios` | — | — | Somente para si | Sim |
| `PUT /horario/bloqueios/{bloqueio_id}` | — | — | Próprio | Sim |
| `DELETE /horario/bloqueios/{bloqueio_id}` | — | — | Próprio | Sim |
| `GET /barbeiro-servico/barbeiro/{barbeiro_id}` | — | — | Próprio | Sim |
| `GET /barbeiro-servico/servico/{service_id}/barbeiros` | — | Sim | — | Sim |
| `POST /barbeiro-servico/` | — | — | — | Sim |
| `DELETE /barbeiro-servico/` | — | — | — | Sim |

\* Refresh e logout não exigem access token, mas exigem o cookie de sessão e validam `Origin` contra a allowlist CORS.

## Regras de propriedade

- Cliente acessa, cancela, reagenda e avalia somente agendamentos cujo `user_id` é o seu. Listas são filtradas pelo usuário autenticado.
- Barbeiro acessa a própria agenda e somente as próprias jornadas e bloqueios. O ID de barbeiro fornecido em criação é comparado ao usuário autenticado.
- Admin pode acessar recursos de outros usuários conforme as rotas administrativas.
- A criação manual por barbeiro ignora `barbeiro_id` enviado no payload e grava o ID autenticado; a validação do horário segue `validate_booking_slot` e `lock_barber_for_booking`.
