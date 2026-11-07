import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import event
from support import access_token_for_user, asgi_request, load_app_for_environment, main, reset_database
from app.models.user import (
    Appointment, AppointmentStatusEnum, BarbearioServico, BloqueioHorario,
    JornadaTrabalho, RoleEnum, Service, User,
)


class BookingCalendarTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("production").app
        self.now = datetime(2030, 1, 7, 9, 15)  # Monday, São Paulo wall time
        with main.SessionLocal() as db:
            client = User(nome="Cliente", email="calendar@example.test", senha_hash="test-only",
                          role=RoleEnum.CLIENTE, consentimento_lgpd=True)
            barber = User(nome="Profissional", email="barber@example.test", senha_hash="test-only",
                          role=RoleEnum.BARBEIRO)
            service = Service(nome="<img src=x onerror=alert(1)>", preco=25, duracao_minutos=60)
            db.add_all([client, barber, service])
            db.flush()
            self.client, self.barber, self.service = client.id, barber.id, service.id
            db.add(BarbearioServico(barbeiro_id=barber.id, service_id=service.id))
            for weekday in (1, 2, 3):
                db.add(JornadaTrabalho(barbeiro_id=barber.id, dia_semana=weekday,
                                       hora_inicio="09:00", hora_fim="12:00", ativo=True))
            db.add(BloqueioHorario(barbeiro_id=barber.id, inicio=datetime(2030, 1, 8),
                                  fim=datetime(2030, 1, 9), tipo="feriado", motivo="test", ativo=True))
            db.add(Appointment(user_id=client.id, barbeiro_id=barber.id, service_id=service.id,
                               data_hora=datetime(2030, 1, 9, 9), duracao_minutos=180,
                               preco=25, status=AppointmentStatusEnum.CONFIRMADO))
            db.commit()
        self.headers = {"Authorization": "Bearer " + access_token_for_user("calendar@example.test")}

    def calendar(self, **params):
        query = {"service_id": self.service, "barbeiro_id": self.barber, **params}
        with patch("app.routers.appointments.now_local", return_value=self.now):
            return asgi_request(self.app, "GET", "/appointments/calendario?" +
                                "&".join(f"{k}={v}" for k, v in query.items()), headers=self.headers)

    def test_distinguishes_working_full_blocked_and_off_without_private_data(self):
        status, data = self.calendar()
        self.assertEqual(status, 200)
        self.assertEqual(len(data["days"]), 15)
        days = {day["date"]: day for day in data["days"]}
        self.assertEqual(days["2030-01-07"]["status"], "available")
        self.assertEqual(days["2030-01-08"]["status"], "blocked")
        self.assertEqual(days["2030-01-09"]["status"], "full")
        self.assertEqual(days["2030-01-10"]["status"], "off")
        self.assertTrue(days["2030-01-09"]["working"])
        self.assertFalse(days["2030-01-10"]["working"])
        self.assertEqual(days["2030-01-07"]["slots"][0]["horario"], "09:30")
        self.assertEqual(days["2030-01-21"]["slots"][0]["horario"], "09:00")
        self.assertEqual(len(days["2030-01-21"]["slots"]), 1)
        self.assertNotIn("motivo", str(data))
        self.assertNotIn("user_id", str(data))

    def test_range_uses_bounded_queries_and_day_endpoint_matches(self):
        queries = []
        def count(conn, cursor, statement, *args):
            if statement.lstrip().upper().startswith("SELECT"):
                queries.append(statement)
        event.listen(main.engine, "before_cursor_execute", count)
        try:
            status, data = self.calendar()
        finally:
            event.remove(main.engine, "before_cursor_execute", count)
        self.assertEqual(status, 200)
        self.assertLessEqual(len(queries), 7)  # auth plus at most 5 availability queries
        with patch("app.routers.appointments.now_local", return_value=self.now):
            status, slots = asgi_request(self.app, "GET",
                f"/appointments/disponiveis?service_id={self.service}&barbeiro_id={self.barber}&data=2030-01-07",
                headers=self.headers)
        self.assertEqual(status, 200)
        self.assertEqual(slots, data["days"][0]["slots"])

    def test_long_service_and_inactive_or_blocked_professional(self):
        with main.SessionLocal() as db:
            db.get(Service, self.service).duracao_minutos = 240
            db.commit()
        status, data = self.calendar()
        self.assertEqual(status, 200)
        self.assertTrue(all(not day["slots"] for day in data["days"]))
        with main.SessionLocal() as db:
            db.get(User, self.barber).bloqueado = True
            db.commit()
        self.assertEqual(self.calendar()[0], 404)

    def test_requires_identity_and_positive_ids(self):
        self.assertEqual(asgi_request(self.app, "GET",
            f"/appointments/calendario?service_id={self.service}&barbeiro_id={self.barber}")[0], 401)
        self.assertEqual(self.calendar(barbeiro_id=0)[0], 422)

    def test_split_shifts_offer_both_periods_and_reject_the_gap(self):
        with main.SessionLocal() as db:
            db.add(JornadaTrabalho(barbeiro_id=self.barber, dia_semana=1,
                                   hora_inicio="13:00", hora_fim="15:00", ativo=True))
            db.commit()
        status, data = self.calendar()
        self.assertEqual(status, 200)
        offered = [slot["horario"] for slot in data["days"][0]["slots"]]
        self.assertIn("09:30", offered)
        self.assertIn("13:00", offered)
        self.assertNotIn("12:30", offered)
        for hour, expected in (("12:30", 400), ("13:00", 201)):
            with patch("app.booking.now_local", return_value=self.now):
                status, _ = asgi_request(self.app, "POST", "/appointments/",
                    {"service_id": self.service, "barbeiro_id": self.barber,
                     "data_hora": f"2030-01-07T{hour}:00"}, headers=self.headers)
            self.assertEqual(status, expected)

    def test_previous_day_overlap_is_not_lost_and_history_is_not_loaded(self):
        with main.SessionLocal() as db:
            db.add(Appointment(user_id=self.client, barbeiro_id=self.barber, service_id=self.service,
                               data_hora=datetime(2030, 1, 6, 23, 30), duracao_minutos=660,
                               preco=25, status=AppointmentStatusEnum.CONFIRMADO))
            db.commit()
        status, data = self.calendar()
        self.assertEqual(status, 200)
        monday = next(day for day in data["days"] if day["date"] == "2030-01-07")
        self.assertEqual(monday["slots"][0]["horario"], "10:30")

    def test_reschedule_projection_keeps_snapshot_duration_and_excludes_itself(self):
        with main.SessionLocal() as db:
            appointment_id = db.query(Appointment.id).scalar()
        status, data = self.calendar(appointment_id=appointment_id)
        self.assertEqual(status, 200)
        wednesday = next(day for day in data["days"] if day["date"] == "2030-01-09")
        self.assertEqual(len(wednesday["slots"]), 1)  # original 180min, not current 60min
        self.assertEqual(wednesday["slots"][0]["horario"], "09:00")
        with main.SessionLocal() as db:
            other = User(nome="Outro cliente", email="other-client@example.test",
                         senha_hash="test-only", role=RoleEnum.CLIENTE, consentimento_lgpd=True)
            db.add(other)
            db.commit()
        self.headers = {"Authorization": "Bearer " + access_token_for_user("other-client@example.test")}
        self.assertEqual(self.calendar(appointment_id=appointment_id)[0], 403)

    def test_invalid_reschedule_does_not_change_persisted_appointment(self):
        with main.SessionLocal() as db:
            appointment_id = db.query(Appointment.id).scalar()
        with patch("app.booking.now_local", return_value=self.now), patch("app.routers.appointments.now_local", return_value=self.now):
            status, _ = asgi_request(self.app, "PUT", f"/appointments/{appointment_id}",
                {"data_hora": "2030-01-10T10:00:00"}, headers=self.headers)
        self.assertEqual(status, 400)
        with main.SessionLocal() as db:
            self.assertEqual(db.get(Appointment, appointment_id).data_hora, datetime(2030, 1, 9, 9))
            self.assertEqual(db.get(Appointment, appointment_id).reschedule_count, 0)

    def test_off_blocked_full_and_outside_window_rejected_on_write(self):
        for start, expected in ((datetime(2030, 1, 10, 10), 400),
                                (datetime(2030, 1, 8, 10), 409),
                                (datetime(2030, 1, 9, 10), 409),
                                (datetime(2030, 1, 22, 10), 400)):
            with patch("app.booking.now_local", return_value=self.now):
                status, _ = asgi_request(self.app, "POST", "/appointments/",
                    {"service_id": self.service, "barbeiro_id": self.barber, "data_hora": start.isoformat()},
                    headers=self.headers)
            self.assertEqual(status, expected)
