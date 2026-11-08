"""Persisted RF23 catalog coverage through existing HTTP lifecycle scenarios."""
import importlib
import json
import re
import unittest
from contextlib import contextmanager

from support import asgi_request, main
from app.models.user import Appointment, AuditLog, Avaliacao, User


class AuditCatalogTests(unittest.TestCase):
    @contextmanager
    def scenario(self, module_name, class_name, method_name):
        # Keep TestCase classes inside their modules so discovery cannot run them
        # a second time merely because this catalog reuses their fixtures.
        module = importlib.import_module(module_name)
        case = getattr(module, class_name)(method_name)
        case.setUp()
        try:
            getattr(case, method_name)()
            yield case
        finally:
            try:
                case.tearDown()
            finally:
                case.doCleanups()

    def events(self, action, entity, role, *, email=None, count=1,
               result="sucesso", entity_id=None, anonymous=False):
        db = main.SessionLocal()
        try:
            rows = db.query(AuditLog).filter_by(acao=action, entidade=entity).order_by(AuditLog.id).all()
            self.assertEqual(len(rows), count, (action, entity))
            actor_id = db.query(User).filter_by(email=email).one().id if email else None
            for row in rows:
                self.assertEqual(row.ator_role, role)
                self.assertEqual(row.resultado, result)
                self.assertEqual(row.ip, "127.0.0.1")
                self.assertIsNotNone(row.ocorrido_em)
                if email:
                    self.assertEqual(row.usuario_id, actor_id)
                elif anonymous:
                    self.assertIsNone(row.usuario_id)
                else:
                    self.assertIsNotNone(row.usuario_id)
                if entity_id is not None:
                    self.assertEqual(row.entidade_id, str(entity_id))
                if entity in {"servico", "jornada", "bloqueio", "informacoes_institucionais",
                              "barbeiro_servico", "avaliacao", "agendamento", "dados_pessoais"}:
                    self.assertTrue(row.entidade_id)
                self.assertIsInstance(row.detalhes, dict)
                for key in row.detalhes:
                    self.assertIsNone(re.search(
                        r"password|senha|token|hash|secret|credential|api[_-]?key|database[_-]?url|authorization|cookie|body|corpo", key, re.I,
                    ), key)
                serialized = json.dumps(row.detalhes)
                for secret in ("session-password", "client-pass-123", "old-pass-123", "new-pass-123"):
                    self.assertNotIn(secret, serialized)
            return rows
        finally:
            db.close()

    def test_service_crud_catalog(self):
        with self.scenario("test_services_crud", "ServiceCrudTests",
                           "test_admin_creates_lists_updates_and_deletes_service"):
            rows = [self.events(f"servico.{suffix}", "servico", "admin",
                                email="service-admin@example.test")[0]
                    for suffix in ("criado", "alterado", "excluido")]
            self.assertTrue(rows[0].entidade_id)
            self.assertEqual(len({row.entidade_id for row in rows}), 1)

    def test_schedule_crud_catalog(self):
        with self.scenario("test_schedule_block_lifecycle", "ScheduleBlockLifecycleTests",
                           "test_owner_can_create_update_and_deactivate_schedule") as case:
            for suffix, count in (("criada", 1), ("alterada", 2), ("excluida", 1)):
                self.events(f"jornada.{suffix}", "jornada", "barbeiro", email=case.barber_email, count=count)

    def test_block_crud_catalog(self):
        with self.scenario("test_schedule_block_lifecycle", "ScheduleBlockLifecycleTests",
                           "test_folga_and_feriado_blocks_edit_deactivate_and_remove_availability") as case:
            for suffix, count in (("criado", 2), ("alterado", 6), ("excluido", 2)):
                self.events(f"bloqueio.{suffix}", "bloqueio", "barbeiro", email=case.barber_email, count=count)

    def test_institution_create_put_and_existing_post_catalog(self):
        with self.scenario("test_institutional_info", "InstitutionalInfoTests",
                           "test_admin_edits_institution_and_public_read_returns_contact_hours_and_map") as case:
            created = self.events("institucional.criada", "informacoes_institucionais", "admin",
                                  email="institucional-admin@example.com")[0]
            self.events("institucional.alterada", "informacoes_institucionais", "admin",
                        email="institucional-admin@example.com", entity_id=created.entidade_id)
            status, payload = asgi_request(case.app, "GET", "/informacoes/")
            self.assertEqual(status, 200)
            payload.pop("id")
            payload["nome"] = "Institucional atualizado por POST"
            status, body = asgi_request(case.app, "POST", "/informacoes/", payload, headers=case.auth)
            self.assertEqual(status, 201, body)
            self.events("institucional.alterada", "informacoes_institucionais", "admin",
                        email="institucional-admin@example.com", count=2, entity_id=created.entidade_id)

    def test_assignment_create_and_remove_catalog(self):
        with self.scenario("test_barber_service_assignments", "BarberServiceAssignmentTests",
                           "test_assignment_adds_barber_to_catalog_and_availability_then_removal_reverses_it") as case:
            created = self.events("associacao.criada", "barbeiro_servico", "admin", email=case.admin_email)[0]
            deleted = self.events("associacao.excluida", "barbeiro_servico", "admin",
                                  email=case.admin_email, entity_id=created.entidade_id)[0]
            self.assertEqual(deleted.detalhes, {"barbeiro_id": case.barber_id, "service_id": case.service_id})

    def test_review_hide_show_catalog(self):
        with self.scenario("test_review_moderation", "ReviewModerationTests",
                           "test_admin_can_hide_and_restore_public_review") as case:
            rows = self.events("avaliacao.moderada", "avaliacao", "admin", email=case.admin_email,
                               count=2, entity_id=case.review_id)
            self.assertEqual([row.detalhes for row in rows], [{"oculta": True}, {"oculta": False}])

    def test_review_creation_catalog_excludes_duplicate_rating(self):
        with self.scenario("test_appointment_reviews", "AppointmentReviewTests",
                           "test_owner_can_rate_concluded_appointment_only_once") as case:
            row = self.events("avaliacao.criada", "avaliacao", "cliente", email=case.owner_email)[0]
            self.assertEqual(row.detalhes, {"nota": 5})
            db = main.SessionLocal()
            try:
                review = db.query(Avaliacao).filter_by(id=int(row.entidade_id)).one()
                self.assertEqual(review.appointment_id, case.concluded_id)
            finally:
                db.close()

    def test_client_cancel_catalog_excludes_rejected_request(self):
        with self.scenario("test_booking_temporal", "BookingTemporalTests",
                           "test_cancel_requires_exactly_twenty_four_hours_or_more"):
            self.events("agendamento.cancelado", "agendamento", "cliente",
                        email="temporal-client@example.test", count=2)

    def test_client_and_manual_creation_catalog_preserves_each_actor(self):
        with self.scenario("test_booking_temporal", "BookingTemporalTests",
                           "test_public_and_admin_creation_keep_price_and_duration_snapshots") as case:
            db = main.SessionLocal()
            try:
                rows = db.query(AuditLog).filter_by(
                    acao="agendamento.criado", entidade="agendamento",
                ).all()
                self.assertEqual(len(rows), 2)
                by_actor = {row.usuario_id: row for row in rows}
                self.assertEqual(set(by_actor), {case.client_id, case.admin_id})
                for actor_id, role, client_id in ((case.client_id, "cliente", case.client_id),
                                                  (case.admin_id, "admin", None)):
                    row = by_actor[actor_id]
                    self.assertEqual(row.ator_role, role)
                    self.assertEqual(row.resultado, "sucesso")
                    self.assertEqual(row.ip, "127.0.0.1")
                    self.assertIsNotNone(row.ocorrido_em)
                    self.assertEqual(row.detalhes, {})
                    appointment = db.query(Appointment).filter_by(id=int(row.entidade_id)).one()
                    self.assertEqual(appointment.user_id, client_id)
            finally:
                db.close()

    def test_client_reschedule_catalog_excludes_rejected_requests(self):
        with self.scenario("test_booking_temporal", "BookingTemporalTests",
                           "test_reschedule_obeys_exact_twenty_four_hour_limit_and_two_change_cap"):
            self.events("agendamento.reagendado", "agendamento", "cliente",
                        email="temporal-client@example.test", count=2)

    def test_team_reschedule_and_cancel_preserve_distinct_actors(self):
        with self.scenario("test_booking_temporal", "BookingTemporalTests",
                           "test_team_permissions_keep_the_existing_client_only_time_and_count_limits"):
            self.events("agendamento.reagendado", "agendamento", "admin",
                        email="temporal-admin@example.test")
            self.events("agendamento.cancelado", "agendamento", "barbeiro",
                        email="temporal-barber@example.test")

    def test_completion_status_and_custom_charge_catalog(self):
        with self.scenario("test_rf14_service_record", "ServiceRecordTests",
                           "test_confirmed_appointment_can_be_completed_after_start_with_custom_charge") as case:
            status = self.events("agendamento.status_alterado", "agendamento", "barbeiro",
                                 email=case.emails["barber"], entity_id=case.appointment_ids[0])[0]
            self.assertEqual(status.detalhes, {"status_anterior": "confirmado", "status_novo": "concluido"})
            charge = self.events("agendamento.valor_alterado", "agendamento", "barbeiro",
                                 email=case.emails["barber"], entity_id=case.appointment_ids[0])[0]
            self.assertEqual(charge.detalhes, {"valor_anterior": None, "valor_novo": 38.5})

    def test_registration_and_login_catalog(self):
        with self.scenario("test_auth_sessions", "AuthenticationSessionTests",
                           "test_registration_records_versioned_consent_and_login_issues_hashed_cookie_token"):
            registered = self.events("usuario.cadastrado", "usuario", "cliente", email="consent@example.com")[0]
            self.assertEqual(registered.entidade_id, str(registered.usuario_id))
            self.events("auth.login", "sessao", "cliente", email="consent@example.com")

    def test_refresh_reuse_catalog(self):
        with self.scenario("test_auth_sessions", "AuthenticationSessionTests",
                           "test_refresh_rotates_token_and_reuse_revokes_the_family"):
            self.events("auth.refresh_reuse", "refresh_token", "cliente",
                        email="rotate@example.com", result="falha")

    def test_logout_catalog(self):
        with self.scenario("test_auth_sessions", "AuthenticationSessionTests", "test_logout_revokes_refresh_token"):
            self.events("auth.logout", "sessao", "cliente", email="logout@example.com")

    def test_password_reset_catalog(self):
        with self.scenario("test_auth_sessions", "AuthenticationSessionTests", "test_password_reset_revokes_refresh_tokens"):
            for action in ("auth.redefinicao_solicitada", "auth.senha_redefinida"):
                self.events(action, "credencial", "cliente", email="password-change@example.com")

    def test_personal_data_export_catalog(self):
        with self.scenario("test_lgpd_portability", "LgpdPortabilityTests",
                           "test_export_is_versioned_complete_and_never_includes_another_user_or_secrets") as case:
            self.events("dados.exportados", "dados_pessoais", "cliente", email="titular@example.com",
                        count=5, entity_id=case.owner_id)

    def test_erasure_catalog_unlinks_actor(self):
        with self.scenario("test_lgpd_portability", "LgpdPortabilityTests",
                           "test_erasure_unlinks_identity_preserves_financial_values_and_blocks_login"):
            erased = self.events("usuario.excluido", "usuario", "cliente", anonymous=True)[0]
            self.assertIsNone(erased.entidade_id)

    def test_financial_report_and_csv_export_catalog(self):
        with self.scenario("test_financial_report", "FinancialReportTests",
                           "test_report_has_inclusive_period_breakdowns_status_counts_and_existing_totals") as case:
            case.test_csv_export_neutralizes_formula_prefixes()
            for entity in ("relatorio_financeiro", "relatorio_financeiro_csv"):
                self.events("dados.exportados", entity, "admin", email=case.emails["admin"])
