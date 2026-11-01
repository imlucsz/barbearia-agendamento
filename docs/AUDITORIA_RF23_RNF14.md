# Evidências RF23 / RNF-14 — 2026-11-01

Escopo: catálogo atual, RF23 (consulta administrativa por usuário/ação/período) e RNF-14 (autenticação, cancelamentos e ações administrativas com usuário, ação, entidade, IP, data/hora, sem credenciais, com retenção). Não há mudança de regras de negócio, schema ou arquitetura.

## Matriz de investigação e fechamento

M = `usuario_id` (quando identificado), `ator_role`, `acao`, `entidade`, `entidade_id` quando aplicável, `ip`, `resultado`, `ocorrido_em` UTC e `detalhes` sanitizados. Ator anônimo é esperado para conta inexistente e desvinculação é esperada após anonimização LGPD. Dados pessoais e credenciais não são copiados para detalhes. O registro persistido é a fonte de metadados completos; JSON de aplicação omite PII deliberadamente.

| Evento exigido / catálogo existente | Gerador | Metadados | Perfil | Teste existente antes desta rodada | Lacuna identificada / fechamento |
|---|---|---|---|---|---|
| `auth.login` sucesso | `auth.login_user` | M, sessão | Cliente/Barbeiro/Admin | `test_audit` login/JSON | Contrato de identidade, IP e horário ampliado |
| `auth.login` falha: senha errada, conta inexistente | `auth.login_user` | M, resultado falha | Público | `test_audit` cobria conta inexistente | Usuário conhecido perdia ID; teste vermelho e correção para `actor=db_user` |
| `auth.login` falha: inativa/bloqueada | `auth.login_user` | M + motivo | Público | Testes de autenticação/perfis | Assert dedicado de ator, perfil, resultado e motivo em `test_audit` |
| `usuario.cadastrado` | `auth.register_user` | M, ID usuário | Público | `test_auth_sessions` | Assert persistido no catálogo |
| `auth.refresh_reuse` | `auth.refresh_session` | M, resultado falha | Usuário da sessão | `test_auth_sessions` rotação/reuso | Assert do evento no catálogo; token revogado não cria evento de reuso artificial |
| `auth.logout` | `auth.logout_session` | M, sessão | Autenticado/anônimo | `test_audit`, `test_auth_sessions` | Ator e entidade conferidos no catálogo |
| `auth.redefinicao_solicitada`, `auth.senha_redefinida` | `auth.esqueci_senha/redefinir_senha` | M, credencial; sem token/senha | Público/titular | `test_password_reset`, `test_brevo_email` | Assert dos eventos no catálogo, envio simulado |
| `agendamento.criado` | `appointments.create_appointment`, `admin.create_manual_appointment` | M, ID agendamento | Cliente/Admin/Barbeiro conforme rota | `test_booking_temporal`, autorização | Catálogo verifica emissão real |
| `agendamento.cancelado`, `agendamento.reagendado` | `appointments.update_appointment` | M + estados quando alterados | Titular/equipe conforme regras existentes | `test_booking_temporal`, `test_rf14_service_record` | Assert persistido específico no catálogo |
| `agendamento.status_alterado`, `agendamento.valor_alterado` | `appointments.update_appointment` | M + estado/valor anterior e novo | Admin/Barbeiro próprio | `test_rf14_service_record` | Catálogo verifica estados/valor sem redefinir matriz RF14 |
| `avaliacao.criada` | `appointments.create_avaliacao` | M + nota | Titular | `test_appointment_reviews` | Evento mantido; caminho já previsto, sem novo evento |
| `servico.criado/alterado/excluido` | `services` CRUD | M, ID serviço | Admin | `test_services_crud`; criação em `test_audit` | Assert por ação no catálogo |
| `jornada.criada/alterada/excluida` | `horario` CRUD jornadas | M, ID jornada | Admin/Barbeiro próprio | `test_schedule_block_lifecycle` | Assert por ação no catálogo |
| `bloqueio.criado/alterado/excluido` | `horario` CRUD bloqueios | M, ID bloqueio | Admin/Barbeiro próprio | `test_schedule_block_lifecycle` | Assert por ação no catálogo |
| `avaliacao.moderada` ocultar/reexibir | `admin.toggle_avaliacao_oculta` | M + oculta | Admin | `test_review_moderation` | Assert dos dois resultados no catálogo |
| `institucional.criada/alterada` | `institucional` POST/PUT | M, ID institucional | Admin | `test_institutional_info` | Catálogo verifica criação e atualização por POST/PUT |
| `associacao.criada/excluida` | `barbeiro_servico` POST/DELETE | M; exclusão inclui IDs barbeiro/serviço | Admin | `test_barber_service_assignments` | Assert persistido por ação no catálogo |
| `usuario.bloqueado/desbloqueado` | `users.update_user` | M; ator admin e ID alvo | Admin | `test_auth_sessions` | Assert dos eventos no catálogo |
| `usuario.alterado` | `users.update_user` | M + nomes dos campos realmente alterados | Admin | Fluxo RF19 sem evento | Falta demonstrada em teste; evento justificado por ação administrativa RF19/RNF-14; sem valores pessoais e sem evento em no-op |
| `dados.exportados` | `users` exportação JSON/PDF; `admin` financeiro/CSV | M + contagens/período conforme rota | Titular/Admin | `test_audit`, portabilidade e financeiro | Catálogo valida rotas e entidades; PDF só audita após sucesso |
| `usuario.excluido` | `users.excluir_minha_conta` | Perfil preservado, identidade removida | Titular | `test_lgpd_portability` | Catálogo verifica desvinculação sem reidentificar usuário |
| `auditoria.consultada` | `admin.listar_auditoria` | M + quantidade | Admin | `test_audit` | Período inclusivo, usuário, ação, entidade, paginação estável e limites em `test_audit` |

Os testes novos de catálogo ficam em `backend/tests/test_audit_catalog.py`. Reutilizam fixtures/cenários reais, consultam `AuditLog` antes do teardown e não substituem `record` por mocks.

## Contratos adicionais

- `test_record_stores_required_metadata_and_filters_secret_fields`: IP e UTC controlados, ator/perfil/ID, exclusão de senha, token, SECRET_KEY, API keys e DATABASE_URL. O teste revelou que BREVO_API_KEY era aceito; o filtro foi corrigido sem capturar valores reais.
- Consulta: filtros combinados, limites inclusivos de período, desempate por ID, total/skip/limit e rejeição de limites inválidos. Cliente e Barbeiro recebem 403. Teste vermelho demonstrou TypeError com timezone misto; filtros agora convertem offsets para UTC sem timezone, mantendo datas naive em UTC e retornando 400 para intervalo invertido após normalização.
- Retenção: `RETENTION_DAYS`, dry-run sem exclusão e expurgo real preservando evento exatamente no limite e eventos recentes; exclusivamente em banco de teste.
- Falha de persistência: mantém o comportamento best-effort existente, não interrompe cadastro e emite aviso sanitizado com request ID, sem texto privado da exceção. Isso não garante trilha persistente durante indisponibilidade do armazenamento; não foi introduzido outbox ou política fail-closed.
- Nenhum endpoint de leitura comum ganha evento novo; não se registra conteúdo de requests, credenciais ou token de recuperação. O aceite externo de RF06 permanece separado.

## Validação

Resultados reais e classificação final estão em `REQUISITOS_STATUS.md`. Este documento é a matriz do escopo; não comprova agendamento de expurgo ou coleta de logs no ambiente publicado.
