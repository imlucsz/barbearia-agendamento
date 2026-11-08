import unittest

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.security import get_password_hash
from app.models.user import RoleEnum, User


class InstitutionalInfoTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("development").app
        db = main.SessionLocal()
        try:
            db.add(User(
                nome="Admin institucional", email="institucional-admin@example.com",
                senha_hash=get_password_hash("institutional-admin-pass"),
                role=RoleEnum.ADMIN, consentimento_lgpd=True,
            ))
            db.commit()
        finally:
            db.close()
        status, body = asgi_request(
            self.app, "POST", "/auth/login",
            {"email": "institucional-admin@example.com", "senha": "institutional-admin-pass"},
        )
        self.assertEqual(status, 200, body)
        self.auth = {"Authorization": f"Bearer {body['access_token']}"}

    def test_admin_edits_institution_and_public_read_returns_contact_hours_and_map(self):
        payload = {
            "nome": "Barbearia Aurora", "endereco": "Rua Aurora, 55",
            "telefone": "+55 11 99999-0000", "email": "contato@example.com",
            "site": "https://example.com", "dias_atendimento": "Segunda a Sábado",
            "horario_funcionamento": "09:00 às 18:00",
            "endereco_maps": "https://www.google.com/maps/place/aurora",
        }
        status, body = asgi_request(self.app, "POST", "/informacoes/", payload, headers=self.auth)
        self.assertEqual(status, 201, body)
        payload["endereco"] = "Avenida Central, 100"
        status, body = asgi_request(self.app, "PUT", "/informacoes/", payload, headers=self.auth)
        self.assertEqual(status, 200, body)
        status, public_info = asgi_request(self.app, "GET", "/informacoes/")
        self.assertEqual(status, 200)
        for field, value in payload.items():
            self.assertEqual(public_info[field], value)

    def test_non_admin_cannot_edit_institutional_info(self):
        status, _body = asgi_request(
            self.app, "POST", "/auth/register",
            {"nome": "Cliente institucional", "email": "cliente-institucional@example.com",
             "senha": "client-institutional-pass", "consentimento_lgpd": True},
            headers={"Origin": "https://frontend.test.invalid"},
        )
        self.assertEqual(status, 201)
        status, body = asgi_request(
            self.app, "POST", "/auth/login",
            {"email": "cliente-institucional@example.com", "senha": "client-institutional-pass"},
        )
        self.assertEqual(status, 200, body)
        client_auth = {"Authorization": f"Bearer {body['access_token']}"}
        status, _body = asgi_request(self.app, "POST", "/informacoes/", {
            "nome": "Loja", "endereco": "Rua 1", "telefone": "11999990000",
            "dias_atendimento": "Todos os dias", "horario_funcionamento": "09:00-18:00",
        }, headers=client_auth)
        self.assertEqual(status, 403)
