import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.security import create_access_token
from app.models.user import (
    Appointment,
    AppointmentStatusEnum,
    BarbearioServico,
    BloqueioHorario,
    JornadaTrabalho,
    RoleEnum,
    Service,
    User,
)


class BookingTemporalTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.application = load_app_for_environment("production").app
        self.fixed_now = datetime(2032, 5, 10, 10, 0, 0)  # Monday, barbershop local time
        self.timezone_patch = patch.dict(os.environ, {"SCHEDULING_TIMEZONE": "America/Sao_Paulo"})
        self.timezone_patch.start()
        self.now_patches = (
            patch("app.booking.now_local", return_value=self.fixed_now),
            patch("app.routers.appointments.now_local", return_value=self.fixed_now),
        )
        for item in self.now_patches:
            item.start()

        db = main.SessionLocal()
        try:
            self.client = self._user(db, "temporal-client@example.test", RoleEnum.CLIENTE)
            self.second_client = self._user(db, "temporal-client-2@example.test", RoleEnum.CLIENTE)
            self.barber = self._user(db, "temporal-barber@example.test", RoleEnum.BARBEIRO)
            self.admin = self._user(db, "temporal-admin@example.test", RoleEnum.ADMIN)
            self.service = Service(nome="Serviço temporal", preco=50, duracao_minutos=60)
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
            db.commit()
            self.client_id = self.client.id
            self.second_client_id = self.second_client.id
            self.barber_id = self.barber.id
            self.admin_id = self.admin.id
            self.service_id = self.service.id
            self.emails = {
                "client": self.client.email,
                "second": self.second_client.email,
                "barber": self.barber.email,
                "admin": self.admin.email,
            }
        finally:
            db.close()

    def tearDown(self):
        for item in self.now_patches:
            item.stop()
        self.timezone_patch.stop()

    @staticmethod
    def _user(db, email, role):
        user = User(
            nome=email.split("@")[0],
            email=email,
            senha_hash="test-only",
            role=role,
            consentimento_lgpd=True,
        )
        db.add(user)
        db.flush()
        return user

    def _token(self, principal="client"):
        return create_access_token({"sub": self.emails[principal]})

    def _book(self, start, principal="client", route="/appointments/"):
        return asgi_request(
            self.application,
            "POST",
            route,
            {"service_id": self.service_id, "barbeiro_id": self.barber_id,
             "data_hora": start.isoformat()},
            headers={"Authorization": f"Bearer {self._token(principal)}"},
        )

    def _appointment(self, start, *, principal="client", status=AppointmentStatusEnum.PENDENTE,
                     duration=60, reschedule_count=0):
        db = main.SessionLocal()
        try:
            row = Appointment(
                user_id=self.client_id if principal == "client" else self.second_client_id,
                nome_cliente="temporal",
                service_id=self.service_id,
                barbeiro_id=self.barber_id,
                data_hora=start,
                status=status,
                preco=50,
                duracao_minutos=duration,
                reschedule_count=reschedule_count,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return row.id
        finally:
            db.close()

    def _stored(self, appointment_id):
        db = main.SessionLocal()
        try:
            row = db.query(Appointment).filter(Appointment.id == appointment_id).one()
            return row.data_hora, row.status, row.reschedule_count, row.preco, row.duracao_minutos
        finally:
            db.close()

    def test_naive_input_is_local_and_offset_input_converts_to_barbershop_timezone(self):
        naive = datetime(2032, 5, 17, 9, 0)
        aware = datetime.fromisoformat("2032-05-17T14:00:00+02:00")
        status, response = self._book(aware)
        self.assertEqual(status, 201)
        self.assertEqual(datetime.fromisoformat(response["data_hora"]), naive)

        second_start = datetime(2032, 5, 18, 11, 0)
        second_status, second_response = self._book(second_start, "second")
        self.assertEqual(second_status, 201)
        self.assertEqual(datetime.fromisoformat(second_response["data_hora"]), second_start)

    def test_offset_block_is_normalized_to_barbershop_local_time(self):
        local_start = datetime(2032, 5, 17, 9, 0)
        status, block = asgi_request(
            self.application, "POST", "/horario/bloqueios",
            {"barbeiro_id": self.barber_id,
             "inicio": "2032-05-17T14:30:00+02:00",
             "fim": "2032-05-17T15:00:00+02:00",
             "tipo": "feriado", "ativo": True},
            headers={"Authorization": f"Bearer {self._token('barber')}"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(datetime.fromisoformat(block["inicio"]), datetime(2032, 5, 17, 9, 30))
        booking_status, _ = self._book(local_start)
        self.assertEqual(booking_status, 409)
        self.assertEqual(self._appointment_count(), 0)

    def test_booking_ending_at_block_start_is_allowed(self):
        block_start = datetime(2032, 5, 17, 10, 30)
        status, _ = asgi_request(
            self.application, "POST", "/horario/bloqueios",
            {"barbeiro_id": self.barber_id,
             "inicio": block_start.isoformat(),
             "fim": (block_start + timedelta(minutes=30)).isoformat(),
             "tipo": "bloqueio_ad_hoc", "ativo": True},
            headers={"Authorization": f"Bearer {self._token('barber')}"},
        )
        self.assertEqual(status, 201)

        booking_status, _ = self._book(block_start - timedelta(minutes=60))
        self.assertEqual(booking_status, 201)
        self.assertEqual(self._appointment_count(), 1)

    def test_jornada_rejects_invalid_day_time_format_and_reversed_interval(self):
        invalid_jornadas = (
            {"dia_semana": 7, "hora_inicio": "09:00", "hora_fim": "18:00"},
            {"dia_semana": 1, "hora_inicio": "9:00", "hora_fim": "18:00"},
            {"dia_semana": 1, "hora_inicio": "18:00", "hora_fim": "09:00"},
        )
        for values in invalid_jornadas:
            with self.subTest(values=values):
                status, _ = asgi_request(
                    self.application, "POST", "/horario/jornadas",
                    {"barbeiro_id": self.barber_id, "ativo": True, **values},
                    headers={"Authorization": f"Bearer {self._token('barber')}"},
                )
                self.assertEqual(status, 422)

        db = main.SessionLocal()
        try:
            self.assertEqual(
                db.query(JornadaTrabalho).filter_by(barbeiro_id=self.barber_id).count(), 7
            )
        finally:
            db.close()

    def test_jornada_update_cannot_invert_existing_interval(self):
        db = main.SessionLocal()
        try:
            jornada_id = db.query(JornadaTrabalho).filter_by(
                barbeiro_id=self.barber_id, dia_semana=1
            ).one().id
        finally:
            db.close()

        status, _ = asgi_request(
            self.application, "PUT", f"/horario/jornadas/{jornada_id}",
            {"hora_inicio": "19:00"},
            headers={"Authorization": f"Bearer {self._token('barber')}"},
        )
        self.assertEqual(status, 400)
        null_status, _ = asgi_request(
            self.application, "PUT", f"/horario/jornadas/{jornada_id}",
            {"hora_inicio": None},
            headers={"Authorization": f"Bearer {self._token('barber')}"},
        )
        self.assertEqual(null_status, 400)
        db = main.SessionLocal()
        try:
            jornada = db.query(JornadaTrabalho).filter_by(id=jornada_id).one()
            self.assertEqual((jornada.hora_inicio, jornada.hora_fim), ("09:00", "18:00"))
        finally:
            db.close()

    def test_service_api_rejects_nonpositive_duration_on_create_and_update(self):
        headers = {"Authorization": f"Bearer {self._token('admin')}"}
        for duration in (0, -1):
            with self.subTest(duration=duration):
                status, _ = asgi_request(
                    self.application, "POST", "/services/",
                    {"nome": "Duração inválida", "preco": 10, "duracao_minutos": duration},
                    headers=headers,
                )
                self.assertEqual(status, 422)

        status, _ = asgi_request(
            self.application, "PUT", f"/services/{self.service_id}",
            {"duracao_minutos": 0}, headers=headers,
        )
        self.assertEqual(status, 422)
        null_status, _ = asgi_request(
            self.application, "PUT", f"/services/{self.service_id}",
            {"duracao_minutos": None}, headers=headers,
        )
        self.assertEqual(null_status, 422)
        db = main.SessionLocal()
        try:
            service = db.query(Service).filter_by(id=self.service_id).one()
            self.assertEqual(service.duracao_minutos, 60)
        finally:
            db.close()

    def test_booking_rejects_past_and_enforces_exact_fourteen_day_instant_boundary(self):
        past_status, _ = self._book(self.fixed_now - timedelta(microseconds=1))
        self.assertEqual(past_status, 400)

        boundary = self.fixed_now + timedelta(days=14)
        exact_status, exact_response = self._book(boundary)
        self.assertEqual(exact_status, 201)
        self.assertEqual(datetime.fromisoformat(exact_response["data_hora"]), boundary)

        after_status, _ = self._book(boundary + timedelta(microseconds=1), "second")
        self.assertEqual(after_status, 400)
        self.assertEqual(self._appointment_count(), 1)

    def _appointment_count(self):
        db = main.SessionLocal()
        try:
            return db.query(Appointment).count()
        finally:
            db.close()

    def test_availability_uses_local_date_and_includes_fourteenth_day(self):
        day = (self.fixed_now + timedelta(days=14)).date().isoformat()
        status, slots = asgi_request(
            self.application, "GET", f"/appointments/disponiveis?service_id={self.service_id}&data={day}",
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(slots)
        too_late = (self.fixed_now + timedelta(days=15)).date().isoformat()
        status, _ = asgi_request(
            self.application, "GET", f"/appointments/disponiveis?service_id={self.service_id}&data={too_late}",
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        self.assertEqual(status, 400)

    def test_overlapping_holiday_block_rejects_public_and_admin_bookings(self):
        start = self.fixed_now + timedelta(days=2)
        block_start = start + timedelta(minutes=30)
        status, _ = asgi_request(
            self.application, "POST", "/horario/bloqueios",
            {"barbeiro_id": self.barber_id, "inicio": block_start.isoformat(),
             "fim": (block_start + timedelta(minutes=30)).isoformat(),
             "tipo": "feriado", "motivo": "Feriado local", "ativo": True},
            headers={"Authorization": f"Bearer {self._token('barber')}"},
        )
        self.assertEqual(status, 201)

        public_status, _ = self._book(start)
        admin_status, _ = asgi_request(
            self.application, "POST", "/admin/agendamentos",
            {"service_id": self.service_id, "barbeiro_id": self.barber_id,
             "nome_cliente": "Reserva administrativa", "data_hora": start.isoformat()},
            headers={"Authorization": f"Bearer {self._token('admin')}"},
        )
        self.assertEqual(public_status, 409)
        self.assertEqual(admin_status, 409)
        self.assertEqual(self._appointment_count(), 0)

    def test_block_requires_positive_interval_and_update_keeps_interval_valid(self):
        start = self.fixed_now + timedelta(days=2)
        invalid_status, _ = asgi_request(
            self.application, "POST", "/horario/bloqueios",
            {"barbeiro_id": self.barber_id, "inicio": start.isoformat(),
             "fim": start.isoformat(), "tipo": "folga"},
            headers={"Authorization": f"Bearer {self._token('barber')}"},
        )
        self.assertEqual(invalid_status, 400)

        db = main.SessionLocal()
        try:
            block = BloqueioHorario(
                barbeiro_id=self.barber_id, inicio=start, fim=start + timedelta(hours=1),
                tipo="bloqueio_ad_hoc", ativo=True,
            )
            db.add(block)
            db.commit()
            block_id = block.id
        finally:
            db.close()
        update_status, _ = asgi_request(
            self.application, "PUT", f"/horario/bloqueios/{block_id}",
            {"fim": start.isoformat()},
            headers={"Authorization": f"Bearer {self._token('barber')}"},
        )
        self.assertEqual(update_status, 400)
        db = main.SessionLocal()
        try:
            persisted = db.query(BloqueioHorario).filter_by(id=block_id).one()
            self.assertEqual(persisted.fim, start + timedelta(hours=1))
        finally:
            db.close()

    def test_cancel_requires_exactly_twenty_four_hours_or_more(self):
        for delta, expected in (
            (timedelta(microseconds=-1), 400),
            (timedelta(0), 200),
            (timedelta(microseconds=1), 200),
        ):
            with self.subTest(delta=delta):
                appointment_id = self._appointment(self.fixed_now + timedelta(hours=24) + delta)
                status, _ = asgi_request(
                    self.application, "PUT", f"/appointments/{appointment_id}",
                    {"status": "cancelado"},
                    headers={"Authorization": f"Bearer {self._token()}"},
                )
                self.assertEqual(status, expected)
                saved = self._stored(appointment_id)
                self.assertEqual(saved[1], AppointmentStatusEnum.CANCELADO if expected == 200 else AppointmentStatusEnum.PENDENTE)

    def test_reschedule_obeys_exact_twenty_four_hour_limit_and_two_change_cap(self):
        for target_offset, (delta, expected) in enumerate((
            (timedelta(microseconds=-1), 400),
            (timedelta(0), 200),
            (timedelta(microseconds=1), 200),
        ), start=3):
            target = self.fixed_now + timedelta(days=target_offset)
            with self.subTest(delta=delta):
                original = self.fixed_now + timedelta(hours=24) + delta
                appointment_id = self._appointment(original)
                status, _ = asgi_request(
                    self.application, "PUT", f"/appointments/{appointment_id}",
                    {"data_hora": target.isoformat()},
                    headers={"Authorization": f"Bearer {self._token()}"},
                )
                self.assertEqual(status, expected)
                saved = self._stored(appointment_id)
                self.assertEqual(saved[0], target if expected == 200 else original)
                self.assertEqual(saved[2], 1 if expected == 200 else 0)

        capped_id = self._appointment(self.fixed_now + timedelta(days=7), reschedule_count=2)
        status, _ = asgi_request(
            self.application, "PUT", f"/appointments/{capped_id}",
            {"data_hora": (self.fixed_now + timedelta(days=8)).isoformat()},
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        self.assertEqual(status, 400)
        capped = self._stored(capped_id)
        self.assertEqual(capped[0], self.fixed_now + timedelta(days=7))
        self.assertEqual(capped[2], 2)

    def test_team_permissions_keep_the_existing_client_only_time_and_count_limits(self):
        soon = self.fixed_now + timedelta(hours=12)
        appointment_id = self._appointment(soon)
        admin_status, _ = asgi_request(
            self.application, "PUT", f"/appointments/{appointment_id}",
            {"data_hora": (self.fixed_now + timedelta(days=3)).isoformat()},
            headers={"Authorization": f"Bearer {self._token('admin')}"},
        )
        self.assertEqual(admin_status, 200)
        self.assertEqual(self._stored(appointment_id)[2], 0)

        barber_status, _ = asgi_request(
            self.application, "PUT", f"/appointments/{appointment_id}",
            {"status": "cancelado"},
            headers={"Authorization": f"Bearer {self._token('barber')}"},
        )
        self.assertEqual(barber_status, 200)
        self.assertEqual(self._stored(appointment_id)[1], AppointmentStatusEnum.CANCELADO)

    def test_invalid_reschedule_rolls_back_and_does_not_increment_count(self):
        original = self.fixed_now + timedelta(days=3)
        appointment_id = self._appointment(original)
        status, _ = asgi_request(
            self.application, "PUT", f"/appointments/{appointment_id}",
            {"data_hora": (self.fixed_now + timedelta(days=3)).replace(hour=18).isoformat()},
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(self._stored(appointment_id)[:3], (original, AppointmentStatusEnum.PENDENTE, 0))

    def test_public_and_admin_creation_keep_price_and_duration_snapshots(self):
        start = self.fixed_now + timedelta(days=2)
        public_status, public = self._book(start)
        admin_start = start + timedelta(hours=2)
        admin_status, admin = asgi_request(
            self.application, "POST", "/admin/agendamentos",
            {"service_id": self.service_id, "barbeiro_id": self.barber_id,
             "nome_cliente": "Avulso temporal", "data_hora": admin_start.isoformat()},
            headers={"Authorization": f"Bearer {self._token('admin')}"},
        )
        self.assertEqual((public_status, admin_status), (201, 201))
        self.assertEqual((public["preco"], public["duracao_minutos"]), (50, 60))
        self.assertEqual((admin["preco"], admin["duracao_minutos"]), (50, 60))
        confirmed_conflict, _ = self._book(admin_start, "second")
        self.assertEqual(confirmed_conflict, 409)

        db = main.SessionLocal()
        try:
            service = db.query(Service).filter_by(id=self.service_id).one()
            service.preco = 99
            service.duracao_minutos = 30
            db.commit()
            rows = db.query(Appointment).order_by(Appointment.id).all()
            self.assertEqual([(row.preco, row.duracao_minutos) for row in rows], [(50, 60), (50, 60)])
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
