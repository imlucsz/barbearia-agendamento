import threading
import unittest
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from support import asgi_request, load_app_for_environment, main, reset_database
from app.booking import now_local
from app.core.security import create_access_token
from app.models.user import (
    Appointment,
    AppointmentStatusEnum,
    BarbearioServico,
    JornadaTrabalho,
    RoleEnum,
    Service,
    User,
)


class BookingIntegrityTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.application = load_app_for_environment("production").app
        expected_dialect = (
            "postgresql"
            if os.environ.get("BOOKING_TEST_BACKEND", "sqlite").strip().lower() == "postgresql"
            else "sqlite"
        )
        self.assertEqual(main.engine.dialect.name, expected_dialect)
        if expected_dialect == "postgresql":
            self.assertTrue((main.engine.url.database or "").lower().endswith("_test"))
        db = main.SessionLocal()
        try:
            self.clients = [
                self._user(db, f"booking-client-{i}@example.test", RoleEnum.CLIENTE)
                for i in range(2)
            ]
            self.barbers = [
                self._user(db, f"booking-barber-{i}@example.test", RoleEnum.BARBEIRO)
                for i in range(2)
            ]
            self.service_60 = Service(nome="Corte 60", preco=40, duracao_minutos=60)
            self.service_30 = Service(nome="Corte 30", preco=25, duracao_minutos=30)
            db.add_all((self.service_60, self.service_30))
            db.flush()
            self.start = (now_local() + timedelta(days=7)).replace(
                hour=12, minute=0, second=0, microsecond=0
            )
            weekday = (self.start.weekday() + 1) % 7
            for barber in self.barbers:
                db.add(JornadaTrabalho(
                    barbeiro_id=barber.id,
                    dia_semana=weekday,
                    hora_inicio="09:00",
                    hora_fim="18:00",
                    ativo=True,
                ))
                db.add_all((
                    BarbearioServico(barbeiro_id=barber.id, service_id=self.service_60.id),
                    BarbearioServico(barbeiro_id=barber.id, service_id=self.service_30.id),
                ))
            db.commit()
            self.client_ids = [user.id for user in self.clients]
            self.barber_ids = [user.id for user in self.barbers]
            self.service_ids = {60: self.service_60.id, 30: self.service_30.id}
            self.client_emails = [user.email for user in self.clients]
        finally:
            db.close()

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

    def _post_booking(self, client_index, barber_index, service_duration, start=None):
        token = create_access_token({"sub": self.client_emails[client_index]})
        return asgi_request(
            self.application,
            "POST",
            "/appointments/",
            {
                "service_id": self.service_ids[service_duration],
                "barbeiro_id": self.barber_ids[barber_index],
                "data_hora": (start or self.start).isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    def _appointments(self):
        db = main.SessionLocal()
        try:
            return db.query(Appointment).order_by(Appointment.id).all()
        finally:
            db.close()

    def _concurrent_requests(self, calls):
        barrier = threading.Barrier(len(calls))
        from app.routers import appointments as appointment_router

        original_lock = appointment_router.lock_barber_for_booking

        def synchronized_lock(db, barber_id):
            # Both independent HTTP requests reach the critical section before
            # either attempts to acquire the database lock.
            barrier.wait(timeout=10)
            return original_lock(db, barber_id)

        with patch.object(appointment_router, "lock_barber_for_booking", synchronized_lock):
            with ThreadPoolExecutor(max_workers=len(calls)) as executor:
                futures = [executor.submit(call) for call in calls]
                return [future.result(timeout=20) for future in futures]

    def test_concurrent_overlapping_bookings_for_same_barber_only_one_persists(self):
        responses = self._concurrent_requests([
            lambda: self._post_booking(0, 0, 60, self.start),
            lambda: self._post_booking(1, 0, 30, self.start + timedelta(minutes=30)),
        ])
        self.assertEqual(sorted(status for status, _ in responses), [201, 409])
        persisted = self._appointments()
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0].barbeiro_id, self.barber_ids[0])

    def test_concurrent_same_service_and_time_for_different_barbers_is_allowed(self):
        responses = self._concurrent_requests([
            lambda: self._post_booking(0, 0, 30),
            lambda: self._post_booking(1, 1, 30),
        ])
        self.assertEqual([status for status, _ in responses], [201, 201])
        persisted = self._appointments()
        self.assertEqual(len(persisted), 2)
        self.assertEqual({row.barbeiro_id for row in persisted}, set(self.barber_ids))

    def test_service_duration_must_fit_inside_working_hours(self):
        closing_edge = self.start.replace(hour=17, minute=30)
        status, _ = self._post_booking(0, 0, 60, closing_edge)
        self.assertEqual(status, 400)
        self.assertEqual(self._appointments(), [])

    def test_canceled_appointment_releases_its_exact_slot(self):
        status, created = self._post_booking(0, 0, 30)
        self.assertEqual(status, 201)
        token = create_access_token({"sub": self.client_emails[0]})
        cancel_status, _ = asgi_request(
            self.application,
            "PUT",
            f"/appointments/{created['id']}",
            {"status": "cancelado"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(cancel_status, 200)
        second_status, _ = self._post_booking(1, 0, 30)
        self.assertEqual(second_status, 201)
        self.assertEqual(len(self._appointments()), 2)

    def test_reschedule_uses_existing_duration_snapshot_and_rolls_back_on_conflict(self):
        status, created = self._post_booking(0, 0, 60)
        self.assertEqual(status, 201)
        db = main.SessionLocal()
        try:
            service = db.query(Service).filter_by(id=self.service_ids[60]).one()
            service.duracao_minutos = 30
            db.commit()
        finally:
            db.close()

        token = create_access_token({"sub": self.client_emails[0]})
        moved_start = self.start + timedelta(hours=1)
        moved_status, moved = asgi_request(
            self.application,
            "PUT",
            f"/appointments/{created['id']}",
            {"data_hora": moved_start.isoformat()},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(moved_status, 200)
        self.assertEqual(moved["duracao_minutos"], 60)

        overlap_status, _ = self._post_booking(
            1, 0, 30, moved_start + timedelta(minutes=30)
        )
        self.assertEqual(overlap_status, 409)
        persisted = self._appointments()
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0].data_hora, moved_start)
        self.assertEqual(persisted[0].duracao_minutos, 60)

    def test_failed_validation_does_not_leave_a_partial_appointment(self):
        invalid_start = self.start.replace(hour=18, minute=0)
        status, _ = self._post_booking(0, 0, 30, invalid_start)
        self.assertEqual(status, 400)
        self.assertEqual(self._appointments(), [])

    def test_persistence_integrity_failure_rolls_back_the_new_appointment(self):
        def fail_before_insert(mapper, connection, target):
            raise IntegrityError("injected test failure", {}, RuntimeError("test"))

        event.listen(Appointment, "before_insert", fail_before_insert)
        try:
            status, _ = self._post_booking(0, 0, 30)
        finally:
            event.remove(Appointment, "before_insert", fail_before_insert)

        self.assertEqual(status, 409)
        self.assertEqual(self._appointments(), [])


if __name__ == "__main__":
    unittest.main()
