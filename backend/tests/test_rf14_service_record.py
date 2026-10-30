import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.security import create_access_token
from app.models.user import (
    Appointment,
    AppointmentStatusEnum,
    AuditLog,
    BarbearioServico,
    JornadaTrabalho,
    RoleEnum,
    Service,
    User,
)


class ServiceRecordTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.fixed_now = datetime(2032, 5, 10, 10, 0, 0)
        self.clock_patches = (
            patch("app.booking.now_local", return_value=self.fixed_now),
            patch("app.routers.appointments.now_local", return_value=self.fixed_now),
        )
        for item in self.clock_patches:
            item.start()
        self.app = load_app_for_environment("development").app
        db = main.SessionLocal()
        try:
            self.client = self._user(db, "rf14-client@example.test", RoleEnum.CLIENTE)
            self.other_client = self._user(db, "rf14-other-client@example.test", RoleEnum.CLIENTE)
            self.barber = self._user(db, "rf14-barber@example.test", RoleEnum.BARBEIRO)
            self.other_barber = self._user(db, "rf14-other-barber@example.test", RoleEnum.BARBEIRO)
            self.admin = self._user(db, "rf14-admin@example.test", RoleEnum.ADMIN)
            self.service = Service(nome="RF14 service", preco=45, duracao_minutos=30)
            db.add(self.service)
            db.flush()
            db.add(BarbearioServico(barbeiro_id=self.barber.id, service_id=self.service.id))
            for weekday in range(7):
                db.add(JornadaTrabalho(
                    barbeiro_id=self.barber.id,
                    dia_semana=weekday,
                    hora_inicio="09:00",
                    hora_fim="18:00",
                    ativo=True,
                ))
            db.flush()
            self.appointment_ids = {}
            future_day = self.fixed_now + timedelta(days=3)
            for index, hour in enumerate((12, 13, 14)):
                appointment = Appointment(
                    user_id=self.client.id,
                    nome_cliente=self.client.nome,
                    service_id=self.service.id,
                    barbeiro_id=self.barber.id,
                    data_hora=future_day.replace(hour=hour),
                    status=AppointmentStatusEnum.PENDENTE,
                    preco=45,
                    duracao_minutos=30,
                )
                db.add(appointment)
                db.flush()
                self.appointment_ids[index] = appointment.id
            db.commit()
            self.emails = {
                "client": self.client.email,
                "other_client": self.other_client.email,
                "barber": self.barber.email,
                "other_barber": self.other_barber.email,
                "admin": self.admin.email,
            }
        finally:
            db.close()

    def tearDown(self):
        for item in self.clock_patches:
            item.stop()

    @staticmethod
    def _user(db, email, role):
        user = User(nome=email, email=email, senha_hash="test-only", role=role)
        db.add(user)
        db.flush()
        return user

    def _update(self, principal, appointment_id, payload):
        token = create_access_token({"sub": self.emails[principal]})
        return asgi_request(
            self.app,
            "PUT",
            f"/appointments/{appointment_id}",
            payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    def _set_appointment(self, appointment_id, *, status=None, data_hora=None):
        db = main.SessionLocal()
        try:
            appointment = db.query(Appointment).filter(Appointment.id == appointment_id).one()
            if status is not None:
                appointment.status = status
            if data_hora is not None:
                appointment.data_hora = data_hora
            db.commit()
        finally:
            db.close()

    def _appointment_state(self, appointment_id):
        db = main.SessionLocal()
        try:
            appointment = db.query(Appointment).filter(Appointment.id == appointment_id).one()
            return appointment.status, appointment.valor_cobrado
        finally:
            db.close()

    def test_team_can_confirm_pending_after_revalidating_slot_and_audits_transition(self):
        appointment_id = self.appointment_ids[0]
        status, result = self._update("barber", appointment_id, {"status": "confirmado"})
        self.assertEqual(status, 200, result)
        self.assertEqual(result["status"], "confirmado")

        db = main.SessionLocal()
        try:
            log = db.query(AuditLog).filter(
                AuditLog.entidade == "agendamento",
                AuditLog.entidade_id == str(appointment_id),
                AuditLog.acao == "agendamento.status_alterado",
            ).one()
            self.assertEqual(log.detalhes, {
                "status_anterior": "pendente",
                "status_novo": "confirmado",
            })
        finally:
            db.close()

    def test_confirmation_rechecks_slot_conflicts(self):
        appointment_id = self.appointment_ids[0]
        conflicting_id = self.appointment_ids[1]
        db = main.SessionLocal()
        try:
            first = db.query(Appointment).filter(Appointment.id == appointment_id).one()
            conflicting = db.query(Appointment).filter(Appointment.id == conflicting_id).one()
            conflicting.data_hora = first.data_hora
            db.commit()
        finally:
            db.close()

        status, _body = self._update("admin", appointment_id, {"status": "confirmado"})
        self.assertEqual(status, 409)
        self.assertEqual(self._appointment_state(appointment_id)[0], AppointmentStatusEnum.PENDENTE)

    def test_team_can_cancel_pending(self):
        status, result = self._update("admin", self.appointment_ids[0], {"status": "cancelado"})
        self.assertEqual(status, 200, result)
        self.assertEqual(result["status"], "cancelado")

    def test_client_can_cancel_pending_at_exact_twenty_four_hour_boundary(self):
        for index, delta, expected in (
            (0, timedelta(microseconds=-1), 400),
            (1, timedelta(0), 200),
            (2, timedelta(microseconds=1), 200),
        ):
            appointment_id = self.appointment_ids[index]
            self._set_appointment(
                appointment_id,
                data_hora=self.fixed_now + timedelta(hours=24) + delta,
            )
            status, _body = self._update("client", appointment_id, {"status": "cancelado"})
            self.assertEqual(status, expected)
            saved_status, _ = self._appointment_state(appointment_id)
            self.assertEqual(
                saved_status,
                AppointmentStatusEnum.CANCELADO if expected == 200 else AppointmentStatusEnum.PENDENTE,
            )

    def test_client_cannot_confirm_pending(self):
        status, _body = self._update("client", self.appointment_ids[0], {"status": "confirmado"})
        self.assertEqual(status, 403)
        self.assertEqual(self._appointment_state(self.appointment_ids[0])[0], AppointmentStatusEnum.PENDENTE)

    def test_team_cannot_complete_mark_absent_or_rate_pending_appointment(self):
        for target in ("concluido", "falta", "avaliado"):
            with self.subTest(target=target):
                appointment_id = self.appointment_ids[0]
                status, _body = self._update("barber", appointment_id, {"status": target})
                self.assertEqual(status, 400)
                self.assertEqual(self._appointment_state(appointment_id), (AppointmentStatusEnum.PENDENTE, None))

    def test_invalid_transition_with_charge_does_not_change_status_or_charge(self):
        appointment_id = self.appointment_ids[0]
        status, _body = self._update(
            "admin", appointment_id, {"status": "concluido", "valor_cobrado": 38.5},
        )
        self.assertEqual(status, 400)
        self.assertEqual(self._appointment_state(appointment_id), (AppointmentStatusEnum.PENDENTE, None))

    def test_team_cannot_record_charge_without_valid_completion_transition(self):
        appointment_id = self.appointment_ids[0]
        status, _body = self._update("barber", appointment_id, {"valor_cobrado": 38.5})
        self.assertEqual(status, 400)
        self.assertEqual(self._appointment_state(appointment_id), (AppointmentStatusEnum.PENDENTE, None))

    def test_confirmed_appointment_can_be_completed_after_start_with_custom_charge(self):
        appointment_id = self.appointment_ids[0]
        self._set_appointment(
            appointment_id,
            status=AppointmentStatusEnum.CONFIRMADO,
            data_hora=self.fixed_now - timedelta(minutes=1),
        )
        status, result = self._update("barber", appointment_id, {
            "status": "concluido", "valor_cobrado": 38.5,
        })
        self.assertEqual(status, 200, result)
        self.assertEqual(result["status"], "concluido")
        self.assertEqual(result["valor_cobrado"], 38.5)

    def test_completion_before_start_is_rejected(self):
        appointment_id = self.appointment_ids[0]
        self._set_appointment(appointment_id, status=AppointmentStatusEnum.CONFIRMADO)
        status, _body = self._update("admin", appointment_id, {"status": "concluido"})
        self.assertEqual(status, 400)
        self.assertEqual(self._appointment_state(appointment_id), (AppointmentStatusEnum.CONFIRMADO, None))

    def test_completion_checks_the_requested_start_when_status_and_time_change_together(self):
        appointment_id = self.appointment_ids[0]
        original_start = self.fixed_now - timedelta(minutes=1)
        requested_start = self.fixed_now + timedelta(days=1)
        self._set_appointment(
            appointment_id,
            status=AppointmentStatusEnum.CONFIRMADO,
            data_hora=original_start,
        )
        status, _body = self._update("admin", appointment_id, {
            "status": "concluido", "data_hora": requested_start.isoformat(),
        })
        self.assertEqual(status, 400)
        saved_status, _ = self._appointment_state(appointment_id)
        self.assertEqual(saved_status, AppointmentStatusEnum.CONFIRMADO)
        db = main.SessionLocal()
        try:
            saved = db.query(Appointment).filter(Appointment.id == appointment_id).one()
            self.assertEqual(saved.data_hora, original_start)
        finally:
            db.close()

    def test_completion_defaults_charged_amount_to_appointment_price(self):
        appointment_id = self.appointment_ids[0]
        self._set_appointment(
            appointment_id,
            status=AppointmentStatusEnum.CONFIRMADO,
            data_hora=self.fixed_now,
        )
        status, result = self._update("admin", appointment_id, {"status": "concluido"})
        self.assertEqual(status, 200, result)
        self.assertEqual(result["valor_cobrado"], 45)

    def test_confirmed_appointment_can_be_marked_absent_only_after_start(self):
        after_start_id = self.appointment_ids[0]
        before_start_id = self.appointment_ids[1]
        self._set_appointment(
            after_start_id,
            status=AppointmentStatusEnum.CONFIRMADO,
            data_hora=self.fixed_now,
        )
        after_status, after_result = self._update("barber", after_start_id, {"status": "falta"})
        self.assertEqual(after_status, 200, after_result)
        self.assertEqual(after_result["status"], "falta")

        self._set_appointment(before_start_id, status=AppointmentStatusEnum.CONFIRMADO)
        before_status, _body = self._update("admin", before_start_id, {"status": "falta"})
        self.assertEqual(before_status, 400)
        self.assertEqual(self._appointment_state(before_start_id)[0], AppointmentStatusEnum.CONFIRMADO)

    def test_team_can_cancel_confirmed_but_client_keeps_twenty_four_hour_rule(self):
        team_id = self.appointment_ids[0]
        client_id = self.appointment_ids[1]
        self._set_appointment(team_id, status=AppointmentStatusEnum.CONFIRMADO)
        team_status, result = self._update("barber", team_id, {"status": "cancelado"})
        self.assertEqual(team_status, 200, result)

        self._set_appointment(
            client_id,
            status=AppointmentStatusEnum.CONFIRMADO,
            data_hora=self.fixed_now + timedelta(hours=24) - timedelta(microseconds=1),
        )
        client_status, _body = self._update("client", client_id, {"status": "cancelado"})
        self.assertEqual(client_status, 400)

    def test_final_states_and_concluded_cannot_transition_through_put(self):
        for index, final_status in enumerate((
            AppointmentStatusEnum.CANCELADO,
            AppointmentStatusEnum.FALTA,
            AppointmentStatusEnum.AVALIADO,
        )):
            appointment_id = self.appointment_ids[index]
            self._set_appointment(appointment_id, status=final_status)
            status, _body = self._update("admin", appointment_id, {"status": "pendente"})
            self.assertEqual(status, 400)
            self.assertEqual(self._appointment_state(appointment_id)[0], final_status)

        appointment_id = self.appointment_ids[0]
        self._set_appointment(appointment_id, status=AppointmentStatusEnum.CONCLUIDO)
        for target in ("confirmado", "cancelado", "falta", "avaliado"):
            with self.subTest(target=target):
                status, _body = self._update("barber", appointment_id, {"status": target})
                self.assertEqual(status, 400)
                self.assertEqual(self._appointment_state(appointment_id)[0], AppointmentStatusEnum.CONCLUIDO)

    def test_admin_and_barber_cannot_set_evaluated_through_put(self):
        for principal in ("admin", "barber"):
            with self.subTest(principal=principal):
                status, _body = self._update(
                    principal, self.appointment_ids[0], {"status": "avaliado"},
                )
                self.assertEqual(status, 400)
                self.assertEqual(
                    self._appointment_state(self.appointment_ids[0])[0],
                    AppointmentStatusEnum.PENDENTE,
                )

    def test_client_cannot_record_team_status_or_charged_amount(self):
        for payload in (
            {"status": "concluido"},
            {"status": "falta"},
            {"valor_cobrado": 38.5},
        ):
            status, _body = self._update("client", self.appointment_ids[0], payload)
            self.assertEqual(status, 403)

    def test_client_and_unassigned_barber_cannot_change_another_owners_appointment(self):
        appointment_id = self.appointment_ids[0]
        other_client_status, _ = self._update("other_client", appointment_id, {"status": "cancelado"})
        other_barber_status, _ = self._update("other_barber", appointment_id, {"status": "confirmado"})
        self.assertEqual(other_client_status, 403)
        self.assertEqual(other_barber_status, 403)
        self.assertEqual(self._appointment_state(appointment_id)[0], AppointmentStatusEnum.PENDENTE)


if __name__ == "__main__":
    unittest.main()
