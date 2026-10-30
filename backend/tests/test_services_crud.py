import unittest

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.security import create_access_token
from app.models.user import RoleEnum, User


class ServiceCrudTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("development").app
        db = main.SessionLocal()
        try:
            self.emails = {}
            for role, email in ((RoleEnum.ADMIN, "service-admin@example.test"), (RoleEnum.CLIENTE, "service-client@example.test")):
                user = User(nome=email, email=email, senha_hash="test-only", role=role)
                db.add(user)
                self.emails[role.value] = email
            db.commit()
        finally:
            db.close()

    def request(self, method, path, payload=None, role="admin"):
        token = create_access_token({"sub": self.emails[role]})
        return asgi_request(
            self.app, method, path, payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    def test_admin_creates_lists_updates_and_deletes_service(self):
        payload = {"nome": "Corte RF16", "descricao": "Corte e acabamento", "preco": 42.5, "duracao_minutos": 45}
        status, created = self.request("POST", "/services/", payload)
        self.assertEqual(status, 201, created)
        service_id = created["id"]
        self.assertEqual(created["descricao"], payload["descricao"])
        status, rows = self.request("GET", "/services/", role="cliente")
        self.assertEqual(status, 200)
        self.assertEqual(rows[0]["id"], service_id)

        status, updated = self.request("PUT", f"/services/{service_id}", {
            "nome": "Corte RF16 atualizado", "preco": 50.0, "duracao_minutos": 60,
        })
        self.assertEqual(status, 200, updated)
        self.assertEqual((updated["nome"], updated["preco"], updated["duracao_minutos"]), ("Corte RF16 atualizado", 50.0, 60))

        status, _body = self.request("DELETE", f"/services/{service_id}")
        self.assertEqual(status, 204)
        status, _body = self.request("GET", f"/services/{service_id}")
        self.assertEqual(status, 404)

    def test_only_admin_can_mutate_services_and_limits_are_validated(self):
        valid = {"nome": "Corte", "descricao": None, "preco": 40.0, "duracao_minutos": 30}
        status, _body = self.request("POST", "/services/", valid, role="cliente")
        self.assertEqual(status, 403)
        for invalid in (
            {**valid, "preco": 0}, {**valid, "preco": 100001},
            {**valid, "duracao_minutos": 0}, {**valid, "duracao_minutos": 1441},
            {**valid, "nome": "x" * 121}, {**valid, "descricao": "x" * 501},
        ):
            status, _body = self.request("POST", "/services/", invalid)
            self.assertEqual(status, 422)
