import unittest
from datetime import timedelta

from support import asgi_request, load_app_for_environment, main, reset_database
from app.booking import now_local
from app.core.security import create_access_token, get_password_hash
from app.models.user import (
    Appointment,
    AppointmentStatusEnum,
    RoleEnum,
    Service,
    User,
)


class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app_module = load_app_for_environment("production")
        self.application = self.app_module.app

        db = main.SessionLocal()
        try:
            self.users = {
                "client_a": self.create_user(db, "client-a@example.com", RoleEnum.CLIENTE),
                "client_b": self.create_user(db, "client-b@example.com", RoleEnum.CLIENTE),
                "barber_a": self.create_user(db, "barber-a@example.com", RoleEnum.BARBEIRO),
                "barber_b": self.create_user(db, "barber-b@example.com", RoleEnum.BARBEIRO),
                "admin": self.create_user(db, "admin@example.com", RoleEnum.ADMIN),
            }
            self.service = Service(nome="Corte", preco=35.0, duracao_minutos=30)
            db.add(self.service)
            db.flush()

            self.appointment_time = (now_local() + timedelta(days=10)).replace(
                hour=12, minute=0, second=0, microsecond=0
            )
            self.appointments = {
                "client_a": self.create_appointment(
                    db, self.users["client_a"], self.users["barber_a"],
                    self.service, self.appointment_time,
                ),
                "client_b": self.create_appointment(
                    db, self.users["client_b"], self.users["barber_b"],
                    self.service, self.appointment_time + timedelta(hours=1),
                ),
            }
            db.commit()
            self.user_ids = {key: user.id for key, user in self.users.items()}
            self.appointment_ids = {
                key: appointment.id for key, appointment in self.appointments.items()
            }
            self.service_id = self.service.id
            self.emails = {key: user.email for key, user in self.users.items()}
        finally:
            db.close()

    @staticmethod
    def create_user(db, email, role):
        user = User(
            nome=email.split("@")[0],
            email=email,
            senha_hash=get_password_hash("test-password"),
            role=role,
            consentimento_lgpd=True,
        )
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def create_appointment(db, client, barber, service, start):
        appointment = Appointment(
            user_id=client.id,
            nome_cliente=client.nome,
            service_id=service.id,
            barbeiro_id=barber.id,
            data_hora=start,
            status=AppointmentStatusEnum.PENDENTE,
            preco=service.preco,
            duracao_minutos=service.duracao_minutos,
        )
        db.add(appointment)
        db.flush()
        return appointment

    def request(self, method, path, payload=None, principal=None):
        headers = {}
        if principal is not None:
            token = create_access_token({"sub": self.emails[principal]})
            headers["Authorization"] = f"Bearer {token}"
        return asgi_request(
            self.application, method, path, payload, headers=headers
        )

    def appointment_snapshot(self):
        db = main.SessionLocal()
        try:
            return [
                (
                    row.id,
                    row.user_id,
                    row.barbeiro_id,
                    row.data_hora,
                    row.status,
                    row.valor_cobrado,
                )
                for row in db.query(Appointment).order_by(Appointment.id).all()
            ]
        finally:
            db.close()

    def client_name(self, client_id):
        db = main.SessionLocal()
        try:
            return db.query(User).filter(User.id == client_id).one().nome
        finally:
            db.close()

    def test_protected_endpoints_return_401_without_authentication(self):
        before = self.appointment_snapshot()
        date_param = self.appointment_time.date().isoformat()
        for path in (
            "/appointments/",
            f"/appointments/{self.appointment_ids['client_a']}",
            f"/admin/agenda?data={date_param}",
            "/users/",
        ):
            with self.subTest(path=path):
                status, _ = self.request("GET", path)
                self.assertEqual(status, 401)
        self.assertEqual(self.appointment_snapshot(), before)

    def test_client_cannot_read_or_modify_another_clients_appointment(self):
        before = self.appointment_snapshot()
        appointment_id = self.appointment_ids["client_b"]

        get_status, _ = self.request(
            "GET", f"/appointments/{appointment_id}", principal="client_a"
        )
        put_status, _ = self.request(
            "PUT", f"/appointments/{appointment_id}",
            {"status": "cancelado"}, principal="client_a",
        )
        delete_status, _ = self.request(
            "DELETE", f"/appointments/{appointment_id}", principal="client_a"
        )

        self.assertEqual(get_status, 403)
        self.assertEqual(put_status, 403)
        self.assertEqual(delete_status, 403)
        self.assertEqual(self.appointment_snapshot(), before)

    def test_owner_can_read_and_cancel_own_appointment(self):
        appointment_id = self.appointment_ids["client_a"]
        get_status, response = self.request(
            "GET", f"/appointments/{appointment_id}", principal="client_a"
        )
        self.assertEqual(get_status, 200)
        self.assertEqual(response["id"], appointment_id)

        update_status, _ = self.request(
            "PUT", f"/appointments/{appointment_id}",
            {"status": "cancelado"}, principal="client_a",
        )
        self.assertEqual(update_status, 200)

        db = main.SessionLocal()
        try:
            appointment = db.query(Appointment).filter(
                Appointment.id == appointment_id
            ).one()
            other = db.query(Appointment).filter(
                Appointment.id == self.appointment_ids["client_b"]
            ).one()
            self.assertEqual(appointment.status, AppointmentStatusEnum.CANCELADO)
            self.assertEqual(appointment.data_hora, self.appointment_time)
            self.assertEqual(other.status, AppointmentStatusEnum.PENDENTE)
        finally:
            db.close()

    def test_barber_sees_only_own_agenda_and_cannot_access_full_or_other_agenda(self):
        date_param = self.appointment_time.date().isoformat()
        own_status, own_agenda = self.request(
            "GET", f"/admin/me/agenda?data={date_param}", principal="barber_a"
        )
        self.assertEqual(own_status, 200)
        self.assertEqual(
            {appointment["id"] for appointment in own_agenda},
            {self.appointment_ids["client_a"]},
        )

        before = self.appointment_snapshot()
        full_status, _ = self.request(
            "GET", f"/admin/agenda?data={date_param}", principal="barber_a"
        )
        other_status, _ = self.request(
            "GET", f"/appointments/{self.appointment_ids['client_b']}",
            principal="barber_a",
        )
        self.assertEqual(full_status, 403)
        self.assertEqual(other_status, 403)
        self.assertEqual(self.appointment_snapshot(), before)

    def test_client_cannot_execute_admin_operations_or_change_data(self):
        before = self.appointment_snapshot()
        old_name = self.client_name(self.user_ids["client_b"])
        date_param = self.appointment_time.date().isoformat()
        manual_appointment = {
            "user_id": self.user_ids["client_a"],
            "service_id": self.service_id,
            "barbeiro_id": self.user_ids["barber_a"],
            "data_hora": (self.appointment_time + timedelta(days=1)).isoformat(),
        }

        users_status, _ = self.request("GET", "/users/", principal="client_a")
        agenda_status, _ = self.request(
            "GET", f"/admin/agenda?data={date_param}", principal="client_a"
        )
        create_status, _ = self.request(
            "POST", "/admin/agendamentos", manual_appointment,
            principal="client_a",
        )
        update_status, _ = self.request(
            "PUT", f"/users/{self.user_ids['client_b']}",
            {"nome": "Alteração indevida"}, principal="client_a",
        )

        self.assertEqual(users_status, 403)
        self.assertEqual(agenda_status, 403)
        self.assertEqual(create_status, 403)
        self.assertEqual(update_status, 403)
        self.assertEqual(self.appointment_snapshot(), before)
        self.assertEqual(self.client_name(self.user_ids["client_b"]), old_name)

    def test_barber_cannot_execute_admin_only_operations(self):
        before = self.appointment_snapshot()
        old_name = self.client_name(self.user_ids["client_b"])
        date_param = self.appointment_time.date().isoformat()
        manual_appointment = {
            "user_id": self.user_ids["client_a"],
            "service_id": self.service_id,
            "barbeiro_id": self.user_ids["barber_a"],
            "data_hora": (self.appointment_time + timedelta(days=1)).isoformat(),
        }

        create_status, _ = self.request(
            "POST", "/admin/agendamentos", manual_appointment,
            principal="barber_a",
        )
        update_status, _ = self.request(
            "PUT", f"/users/{self.user_ids['client_b']}",
            {"nome": "Alteração indevida"}, principal="barber_a",
        )
        report_status, _ = self.request(
            "GET", f"/admin/relatorio?inicio={date_param}&fim={date_param}",
            principal="barber_a",
        )

        self.assertEqual(create_status, 403)
        self.assertEqual(update_status, 403)
        self.assertEqual(report_status, 403)
        self.assertEqual(self.appointment_snapshot(), before)
        self.assertEqual(self.client_name(self.user_ids["client_b"]), old_name)

    def test_client_and_barber_cannot_call_remaining_admin_write_operations(self):
        date_param = self.appointment_time.date().isoformat()
        institutional = {
            "nome": "Barbearia",
            "endereco": "Rua de teste, 1",
            "telefone": "11999999999",
            "horario_funcionamento": "09:00-18:00",
            "dias_atendimento": "Segunda a sábado",
        }
        forbidden_calls = (
            ("POST", "/services/", {"nome": "Corte novo", "preco": 10, "duracao_minutos": 30}),
            ("PUT", f"/services/{self.service_id}", {"nome": "Corte alterado"}),
            ("DELETE", f"/services/{self.service_id}", None),
            ("GET", "/admin/avaliacoes", None),
            ("PATCH", "/admin/avaliacoes/999/ocultar?ocultar=true", None),
            ("POST", "/informacoes/", institutional),
            ("PUT", "/informacoes/", institutional),
            ("POST", "/barbeiro-servico/", {
                "barbeiro_id": self.user_ids["barber_a"], "service_id": self.service_id,
            }),
            ("DELETE", f"/barbeiro-servico/?barbeiro_id={self.user_ids['barber_a']}&service_id={self.service_id}", None),
            ("GET", "/users/barbeiros", None),
            ("GET", f"/users/{self.user_ids['client_b']}", None),
            ("GET", f"/admin/relatorio?inicio={date_param}&fim={date_param}", None),
        )
        for principal in ("client_a", "barber_a"):
            for method, path, payload in forbidden_calls:
                with self.subTest(principal=principal, method=method, path=path):
                    status, _ = self.request(method, path, payload, principal)
                    self.assertEqual(status, 403)

    def test_user_responses_do_not_expose_password_hash_or_consent_metadata(self):
        token = create_access_token({"sub": self.emails["client_a"]})
        status, user = asgi_request(
            self.application,
            "GET",
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(status, 200)
        self.assertEqual(
            set(user), {"email", "nome", "id", "role", "bloqueado"}
        )
        for private_field in ("senha_hash", "consentimento_lgpd", "consentimento_em", "ativo"):
            self.assertNotIn(private_field, user)

    def test_admin_can_read_full_agenda_and_update_authorized_client_data(self):
        date_param = self.appointment_time.date().isoformat()
        agenda_status, agenda = self.request(
            "GET", f"/admin/agenda?data={date_param}", principal="admin"
        )
        self.assertEqual(agenda_status, 200)
        self.assertEqual(
            {appointment["id"] for appointment in agenda},
            set(self.appointment_ids.values()),
        )

        own_resource_status, _ = self.request(
            "GET", f"/appointments/{self.appointment_ids['client_a']}",
            principal="admin",
        )
        update_status, _ = self.request(
            "PUT", f"/users/{self.user_ids['client_b']}",
            {"nome": "Cliente atualizado"}, principal="admin",
        )
        self.assertEqual(own_resource_status, 200)
        self.assertEqual(update_status, 200)
        self.assertEqual(self.client_name(self.user_ids["client_b"]), "Cliente atualizado")


if __name__ == "__main__":
    unittest.main()
