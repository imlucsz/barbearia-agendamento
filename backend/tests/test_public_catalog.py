import unittest

from support import asgi_request, load_app_for_environment, main, reset_database
from app.models.user import Service


class PublicCatalogTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("development").app
        db = main.SessionLocal()
        try:
            db.add(Service(nome="Corte executivo", descricao="Acabamento e lavagem", preco=42.5, duracao_minutos=45))
            db.commit()
        finally:
            db.close()

    def test_public_services_include_description_price_and_duration(self):
        status, body = asgi_request(self.app, "GET", "/services/")
        self.assertEqual(status, 200)
        self.assertEqual(body[0]["nome"], "Corte executivo")
        self.assertEqual(body[0]["descricao"], "Acabamento e lavagem")
        self.assertEqual(body[0]["preco"], 42.5)
        self.assertEqual(body[0]["duracao_minutos"], 45)
