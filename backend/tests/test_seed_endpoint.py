import unittest
from support import asgi_request, load_app_for_environment, main, reset_database
from app.models.user import Service, User


class SeedEndpointTests(unittest.TestCase):
    def setUp(self):
        reset_database()

    def demo_data_counts(self, application):
        db = application.SessionLocal()
        try:
            return (
                db.query(User).count(),
                db.query(Service).count(),
            )
        finally:
            db.close()

    def test_seed_route_is_not_registered_when_app_env_is_missing(self):
        application = load_app_for_environment(None)

        self.assertEqual(application.APP_ENV, "")
        status, _ = asgi_request(application.app, "GET", "/seed")
        self.assertEqual(status, 404)
        self.assertEqual(self.demo_data_counts(application), (0, 0))

    def test_seed_route_is_not_registered_outside_development(self):
        application = load_app_for_environment("production")

        self.assertEqual(application.APP_ENV, "production")
        status, _ = asgi_request(application.app, "GET", "/seed")
        self.assertEqual(status, 404)
        self.assertEqual(self.demo_data_counts(application), (0, 0))

    def test_development_seed_creates_demo_data_without_returning_credentials(self):
        application = load_app_for_environment("development")

        self.assertEqual(application.APP_ENV, "development")
        status, response = asgi_request(application.app, "GET", "/seed")

        self.assertEqual(status, 200)
        self.assertEqual(
            response,
            {"message": "Dados de demonstração criados com sucesso"},
        )
        self.assertEqual(self.demo_data_counts(application), (3, 5))
        self.assertNotIn("admin123", str(response))
        self.assertNotIn("barbeiro123", str(response))
        self.assertNotIn("cliente123", str(response))


if __name__ == "__main__":
    unittest.main()
