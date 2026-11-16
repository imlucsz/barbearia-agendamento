from support import access_token_for_user
import os
import unittest
from datetime import timedelta
from unittest.mock import patch

from support import asgi_request, load_app_for_environment, main, reset_database
from app.booking import now_local
from app.models.user import (
    Appointment,
    AppointmentStatusEnum,
    BarbearioServico,
    JornadaTrabalho,
    RoleEnum,
    Service,
    User,
)


class BookingAbuseLimitTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.application = load_app_for_environment("production").app
        db = main.SessionLocal()
        try:
            users = {
                name: User(
                    nome=f"abuse-{name}", email=f"abuse-{name}@example.test", senha_hash="test-only",
                    role=role, consentimento_lgpd=True,
                )
                for name, role in (
                    ("client", RoleEnum.CLIENTE), ("other", RoleEnum.CLIENTE),
                    ("barber", RoleEnum.BARBEIRO), ("admin", RoleEnum.ADMIN),
                )
            }
            db.add_all(users.values())
            self.service = Service(nome="Corte 30", preco=25, duracao_minutos=30)
            db.add(self.service)
            db.flush()
            self.day = (now_local() + timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            db.add(JornadaTrabalho(
                barbeiro_id=users["barber"].id, dia_semana=(self.day.weekday() + 1) % 7,
                hora_inicio="09:00", hora_fim="18:00", ativo=True,
            ))
            db.add(BarbearioServico(barbeiro_id=users["barber"].id, service_id=self.service.id))
            db.commit()
            self.ids = {name: user.id for name, user in users.items()}
            self.emails = {name: user.email for name, user in users.items()}
            self.service_id = self.service.id
        finally:
            db.close()

    def _at(self, hour, minute=0, second=0, microsecond=0):
        return self.day.replace(hour=hour, minute=minute, second=second, microsecond=microsecond)

    def _request(self, method, path, payload, principal):
        token = access_token_for_user(self.emails[principal])
        return asgi_request(self.application, method, path, payload, headers={"Authorization": f"Bearer {token}"})

    def _book(self, start, principal="client"):
        return self._request("POST", "/appointments/", {
            "service_id": self.service_id, "barbeiro_id": self.ids["barber"], "data_hora": start.isoformat(),
        }, principal)

    def _admin_book(self, start):
        return self._request("POST", "/admin/agendamentos", {
            "service_id": self.service_id, "barbeiro_id": self.ids["barber"],
            "nome_cliente": "Cliente avulso", "data_hora": start.isoformat(),
        }, "admin")

    def _count(self, **filters):
        db = main.SessionLocal()
        try:
            return db.query(Appointment).filter_by(**filters).count()
        finally:
            db.close()

    def _insert(self, start, status, user="client"):
        db = main.SessionLocal()
        try:
            db.add(Appointment(
                user_id=self.ids[user], nome_cliente="abuse", service_id=self.service_id,
                barbeiro_id=self.ids["barber"], data_hora=start, status=status, preco=25, duracao_minutos=30,
            ))
            db.commit()
        finally:
            db.close()

    def test_client_cannot_exceed_default_active_booking_limit(self):
        for hour in (9, 10, 11):
            self.assertEqual(self._book(self._at(hour))[0], 201)
        status, body = self._book(self._at(12))
        self.assertEqual(status, 409)
        self.assertIn("Limite de 3 agendamentos ativos", body["detail"])
        self.assertEqual(self._count(user_id=self.ids["client"]), 3)
        self.assertEqual(self._book(self._at(12), principal="other")[0], 201)

    def test_cancelled_and_past_bookings_do_not_count_toward_limit(self):
        self._insert(self._at(9), AppointmentStatusEnum.CANCELADO)
        self._insert(self._at(9, 30), AppointmentStatusEnum.CONCLUIDO)
        self._insert(now_local() - timedelta(days=1), AppointmentStatusEnum.CONFIRMADO)
        self._insert(now_local() - timedelta(days=2), AppointmentStatusEnum.PENDENTE)
        for hour in (10, 11, 12):
            self.assertEqual(self._book(self._at(hour))[0], 201)
        self.assertEqual(self._book(self._at(13))[0], 409)

    def test_confirmed_bookings_count_toward_limit(self):
        self._insert(self._at(9), AppointmentStatusEnum.CONFIRMADO)
        self._insert(self._at(10), AppointmentStatusEnum.CONFIRMADO)
        self._insert(self._at(11), AppointmentStatusEnum.PENDENTE)
        self.assertEqual(self._book(self._at(12))[0], 409)

    def test_active_booking_limit_is_configurable(self):
        with patch.dict(os.environ, {"MAX_ACTIVE_APPOINTMENTS_PER_CLIENT": "1"}):
            self.assertEqual(self._book(self._at(9))[0], 201)
            self.assertEqual(self._book(self._at(10))[0], 409)
        self.assertEqual(self._count(user_id=self.ids["client"]), 1)

    def test_admin_manual_booking_ignores_client_limit(self):
        for hour in (9, 10, 11):
            self._insert(self._at(hour), AppointmentStatusEnum.PENDENTE)
        status, _ = self._request("POST", "/admin/agendamentos", {
            "service_id": self.service_id, "barbeiro_id": self.ids["barber"],
            "user_id": self.ids["client"], "data_hora": self._at(12).isoformat(),
        }, "admin")
        self.assertEqual(status, 201)

    def test_client_booking_must_follow_slot_grid(self):
        for start in (self._at(10, 15), self._at(10, 0, 30), self._at(10, 0, 0, 1), self._at(10, 29)):
            with self.subTest(start=start.isoformat()):
                status, body = self._book(start)
                self.assertEqual(status, 400)
                self.assertIn("grade de 30 minutos", body["detail"])
        self.assertEqual(self._count(), 0)
        self.assertEqual(self._book(self._at(10, 30))[0], 201)

    def test_slot_grid_is_anchored_to_schedule_opening(self):
        db = main.SessionLocal()
        try:
            db.query(JornadaTrabalho).update({"hora_inicio": "09:15"})
            db.commit()
        finally:
            db.close()
        self.assertEqual(self._book(self._at(10))[0], 400)
        self.assertEqual(self._book(self._at(9, 45))[0], 201)

    def test_overlapping_shifts_accept_start_on_either_grid(self):
        db = main.SessionLocal()
        try:
            schedule = db.query(JornadaTrabalho).one()
            schedule.hora_fim = "12:00"
            db.add(JornadaTrabalho(
                barbeiro_id=schedule.barbeiro_id, dia_semana=schedule.dia_semana,
                hora_inicio="10:15", hora_fim="14:00", ativo=True,
            ))
            db.commit()
        finally:
            db.close()
        self.assertEqual(self._book(self._at(10, 45))[0], 201)
        self.assertEqual(self._book(self._at(11, 30))[0], 201)
        self.assertEqual(self._book(self._at(12, 50))[0], 400)

    def test_admin_manual_booking_keeps_accepting_off_grid_start(self):
        status, body = self._admin_book(self._at(10, 15))
        self.assertEqual(status, 201)
        self.assertEqual(body["status"], AppointmentStatusEnum.CONFIRMADO.value)

    def test_client_reschedule_must_follow_grid_but_admin_reschedule_does_not(self):
        status, created = self._book(self._at(10))
        self.assertEqual(status, 201)
        path = f"/appointments/{created['id']}"
        self.assertEqual(self._request("PUT", path, {"data_hora": self._at(11, 15).isoformat()}, "client")[0], 400)
        self.assertEqual(self._request("PUT", path, {"data_hora": self._at(11).isoformat()}, "client")[0], 200)
        self.assertEqual(self._request("PUT", path, {"data_hora": self._at(12, 15).isoformat()}, "admin")[0], 200)

    def test_confirming_legacy_off_grid_booking_still_works(self):
        self._insert(self._at(10, 15), AppointmentStatusEnum.PENDENTE)
        db = main.SessionLocal()
        try:
            appointment_id = db.query(Appointment.id).scalar()
        finally:
            db.close()
        status, body = self._request(
            "PUT", f"/appointments/{appointment_id}", {"status": AppointmentStatusEnum.CONFIRMADO.value}, "admin",
        )
        self.assertEqual(status, 200, body)


if __name__ == "__main__":
    unittest.main()
