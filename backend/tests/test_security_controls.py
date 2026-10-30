import os
import unittest
from datetime import timedelta
from unittest.mock import patch

from support import asgi_request, load_app_for_environment, main, reset_database
from test_application_configuration import _asgi_exchange
from app.core.clock import utc_now_naive
from app.models.user import LoginAttempt, RoleEnum, User
from app.core.security import get_password_hash


class SecurityControlTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        os.environ["RATE_LIMIT_MAX_ATTEMPTS"] = "5"
        os.environ["RATE_LIMIT_BLOCK_MINUTES"] = "15"
        os.environ["FORCE_HTTPS"] = "false"
        os.environ["CLIENT_IP_SOURCE"] = "direct"
        self.app = load_app_for_environment("development").app

    def tearDown(self):
        os.environ.pop("RATE_LIMIT_MAX_ATTEMPTS", None)
        os.environ.pop("RATE_LIMIT_BLOCK_MINUTES", None)
        os.environ.pop("FORCE_HTTPS", None)
        os.environ.pop("CLIENT_IP_SOURCE", None)

    def post_login(self, ip="127.0.0.1", password="wrong", headers=None):
        return asgi_request(self.app, "POST", "/auth/login", {"email": "none@example.com", "senha": password}, headers=headers, client_ip=ip, return_headers=True)

    def test_five_failures_block_and_different_ips_are_independent(self):
        for _ in range(4):
            self.assertEqual(self.post_login()[0], 401)
        self.assertEqual(self.post_login("127.0.0.2")[0], 401)
        status, _body, headers = self.post_login()
        self.assertEqual(status, 429)
        self.assertGreater(int(headers["retry-after"]), 0)
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        self.assertEqual(self.post_login("127.0.0.2")[0], 401)

    def test_forwarded_headers_cannot_change_rate_limit_bucket_in_direct_mode(self):
        for _ in range(4):
            self.assertEqual(self.post_login()[0], 401)
        status = self.post_login(headers={
            "X-Forwarded-For": "127.0.0.2",
            "X-Real-IP": "127.0.0.2",
            "CF-Connecting-IP": "127.0.0.2",
        })[0]
        self.assertEqual(status, 429)

    def test_trusted_edge_ips_use_separate_rate_limit_buckets(self):
        os.environ["CLIENT_IP_SOURCE"] = "cf-connecting-ip"
        first = {"CF-Connecting-IP": "198.51.100.10"}
        second = {"CF-Connecting-IP": "198.51.100.11"}
        for _ in range(4):
            self.assertEqual(self.post_login(ip="10.0.0.5", headers=first)[0], 401)
        self.assertEqual(self.post_login(ip="10.0.0.5", headers=first)[0], 429)
        self.assertEqual(self.post_login(ip="10.0.0.5", headers=second)[0], 401)

    def test_success_resets_consecutive_failure_count(self):
        for _ in range(4):
            self.post_login()
        db = main.SessionLocal()
        try:
            db.add(User(nome="Test", email="good@example.com", senha_hash=get_password_hash("secret123"), role=RoleEnum.CLIENTE))
            db.commit()
        finally:
            db.close()
        status = asgi_request(self.app, "POST", "/auth/login", {"email": "good@example.com", "senha": "secret123"})[0]
        self.assertEqual(status, 200)
        self.assertEqual(self.post_login()[0], 401)

    def test_expired_block_allows_attempt_again(self):
        for _ in range(5):
            self.post_login()
        db = main.SessionLocal()
        try:
            old_time = utc_now_naive() - timedelta(days=365)
            db.query(LoginAttempt).update({LoginAttempt.ocorrido_em: old_time})
            db.commit()
        finally:
            db.close()
        self.assertEqual(self.post_login()[0], 401)

    def test_security_headers_are_present_and_hsts_is_production_only(self):
        status, headers = _asgi_exchange(self.app, "GET", {})
        self.assertEqual(status, 200)
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        self.assertIn("frame-ancestors 'none'", headers["content-security-policy"])
        self.assertNotIn("strict-transport-security", headers)

        with patch("app.main.SECURITY_SETTINGS", type("S", (), {"force_https": False, "app_env": "production"})()):
            status, headers = _asgi_exchange(self.app, "GET", {})
        self.assertEqual(status, 200)
        self.assertIn("max-age=31536000", headers["strict-transport-security"])

    def test_https_redirect_does_not_trust_forwarded_scheme_headers(self):
        configured = type("S", (), {"force_https": True, "app_env": "production"})()
        with patch("app.main.SECURITY_SETTINGS", configured):
            messages = []

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                messages.append(message)

            import asyncio
            scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "GET",
                     "scheme": "http", "path": "/health", "raw_path": b"/health", "query_string": b"",
                     "root_path": "", "headers": [(b"host", b"testserver"), (b"x-forwarded-proto", b"https")],
                     "client": ("127.0.0.1", 12345), "server": ("testserver", 80)}
            asyncio.run(self.app(scope, receive, send))
            response = next(message for message in messages if message["type"] == "http.response.start")
            self.assertEqual(response["status"], 307)
            self.assertIn((b"location", b"https://testserver/health"), response["headers"])

        with patch("app.main.SECURITY_SETTINGS", configured):
            messages.clear()
            asyncio.run(self.app(scope, receive, send))
            response = next(message for message in messages if message["type"] == "http.response.start")
            self.assertEqual(response["status"], 307)


if __name__ == "__main__":
    unittest.main()
