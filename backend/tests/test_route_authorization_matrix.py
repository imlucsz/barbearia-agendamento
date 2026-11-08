import unittest

from support import load_app_for_environment
from app.dependencies import get_current_user


PUBLIC_ROUTES = {
    ("GET", "/openapi.json"), ("HEAD", "/openapi.json"),
    ("GET", "/docs"), ("HEAD", "/docs"),
    ("GET", "/docs/oauth2-redirect"), ("HEAD", "/docs/oauth2-redirect"),
    ("GET", "/redoc"), ("HEAD", "/redoc"),
    ("GET", "/"), ("GET", "/health"), ("GET", "/ready"), ("GET", "/metrics"),
    ("POST", "/auth/register"), ("POST", "/auth/login"),
    ("POST", "/auth/refresh"), ("POST", "/auth/logout"),
    ("POST", "/auth/esqueci-senha"), ("POST", "/auth/redefinir-senha"),
    ("GET", "/services/"), ("GET", "/services/{service_id}"),
    ("GET", "/informacoes/"), ("GET", "/appointments/avaliacoes"),
}


def _all_api_routes(routes):
    for route in routes:
        if hasattr(route, "original_router"):
            yield from _all_api_routes(route.original_router.routes)
        elif hasattr(route, "path") and hasattr(route, "methods"):
            yield route


def _dependency_calls(dependant):
    for dependency in dependant.dependencies:
        yield dependency.call
        yield from _dependency_calls(dependency)


class RouteAuthorizationMatrixTests(unittest.TestCase):
    def test_every_non_public_route_declares_authentication_or_role_policy(self):
        application = load_app_for_environment("test").app
        discovered = set()
        for route in _all_api_routes(application.routes):
            for method in route.methods or ():
                key = (method, route.path)
                discovered.add(key)
                if key in PUBLIC_ROUTES:
                    continue
                with self.subTest(method=method, path=route.path):
                    if not hasattr(route, "dependant"):
                        self.fail("Rota não declarada como pública nem autenticada")
                    calls = set(_dependency_calls(route.dependant))
                    self.assertIn(get_current_user, calls, "Rota privada sem autenticação declarada")

        self.assertEqual(PUBLIC_ROUTES - discovered, set(), "A lista de rotas públicas contém rota inexistente")


if __name__ == "__main__":
    unittest.main()
