import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from unittest.mock import patch

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.security import get_password_hash
from app.models.user import LoginAttempt, User, RoleEnum


class LoginRateLimitTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("development").app
        import os
        os.environ["CLIENT_IP_SOURCE"] = "direct"
        self.now = datetime(2026, 11, 5, 12)
        self.clock = patch("app.core.login_rate_limit.utc_now_naive", side_effect=lambda: self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        db = main.SessionLocal()
        try:
            db.add(User(nome="Teste", email="good@example.com", senha_hash=get_password_hash("correct-password"), role=RoleEnum.CLIENTE))
            db.commit()
        finally:
            db.close()

    def login(self, email="absent@example.com", ip="127.0.0.1", password="wrong", headers=None):
        return asgi_request(self.app, "POST", "/auth/login", {"email": email, "senha": password},
                            client_ip=ip, headers=headers, return_headers=True)

    def test_account_normalization_cross_ip_and_shared_network(self):
        for i in range(5):
            self.assertEqual(self.login(email="  Absent@EXAMPLE.COM ", ip=f"127.0.0.{i + 1}")[0], 401)
        status, body, headers = self.login(ip="127.0.0.10")
        self.assertEqual(status, 429)
        self.assertEqual(headers["retry-after"], "60")
        self.assertEqual(body, {"detail": "Muitas tentativas. Tente novamente mais tarde."})
        self.assertEqual(self.login(email="other@example.com")[0], 401)
        self.assertEqual(self.login(email="good@example.com", password="correct-password")[0], 200)

    def test_ip_failures_limit_across_accounts_and_expiration(self):
        for i in range(30):
            self.assertEqual(self.login(email=f"absent{i}@example.com")[0], 401)
        with patch("app.routers.auth.verify_password_and_update") as verify:
            status, _, headers = self.login(email="good@example.com", password="correct-password")
            self.assertEqual(status, 429)
            verify.assert_not_called()
        self.assertEqual(headers["retry-after"], "300")
        self.assertEqual(self.login(ip="127.0.0.2")[0], 401)
        self.now += timedelta(seconds=300)
        self.assertEqual(self.login()[0], 401)

    def test_success_frequency_is_limited_before_password_work(self):
        with patch("app.routers.auth.verify_password_and_update", return_value=(True, None)) as verify:
            for _ in range(60):
                self.assertEqual(self.login(email="good@example.com", password="correct-password")[0], 200)
            self.assertEqual(self.login(email="good@example.com", password="correct-password")[0], 429)
            self.assertEqual(verify.call_count, 60)
            self.now += timedelta(seconds=60)
            self.assertEqual(self.login(email="good@example.com", password="correct-password")[0], 200)

    def test_account_block_does_not_slide_or_reveal_existence(self):
        for email in ("absent@example.com", "good@example.com"):
            for _ in range(5):
                self.assertEqual(self.login(email=email)[0], 401)
            self.now += timedelta(seconds=10)
            status, body, headers = self.login(email=email)
            self.assertEqual(status, 429)
            self.assertEqual(headers["retry-after"], "50")
            self.assertEqual(body["detail"], "Muitas tentativas. Tente novamente mais tarde.")
            self.now += timedelta(seconds=50)
            self.assertEqual(self.login(email=email)[0], 401)

    def test_atomic_reservations_and_failure_budget(self):
        from app.core import login_rate_limit as limiter
        from dataclasses import replace
        with patch.object(limiter, "POLICY", replace(limiter.POLICY, account_concurrency=10, ip_concurrency=10)):
            def reserve(i):
                try:
                    return limiter.reserve(f"127.0.0.{i + 1}", "same@example.com")
                except limiter.Limited:
                    return None
            with ThreadPoolExecutor(max_workers=8) as pool:
                reservations = list(pool.map(reserve, range(8)))
        self.assertEqual(sum(item is not None for item in reservations), 5)
        db = main.SessionLocal()
        try:
            rows = db.query(LoginAttempt).all()
            self.assertEqual(len(rows), 5)
            self.assertTrue(all(row.em_andamento for row in rows))
            self.assertTrue(all(row.account_key and "@" not in row.account_key for row in rows))
        finally:
            db.close()

    def test_concurrency_is_per_account_and_ip_and_leases_expire(self):
        from app.core import login_rate_limit as limiter
        first = limiter.reserve("127.0.0.1", "same@example.com")
        limiter.reserve("127.0.0.2", "same@example.com")
        with self.assertRaises(limiter.Limited) as caught:
            limiter.reserve("127.0.0.3", "same@example.com")
        self.assertEqual(caught.exception.retry_after, 120)
        limiter.finish(first, limiter.Outcome.SUCCESS, limiter.Reason.AUTHENTICATED)
        limiter.reserve("127.0.0.3", "same@example.com")
        limiter.reserve("127.0.0.1", "other1@example.com")
        limiter.reserve("127.0.0.1", "other2@example.com")
        limiter.reserve("127.0.0.1", "other3@example.com")
        limiter.reserve("127.0.0.1", "other4@example.com")
        with self.assertRaises(limiter.Limited):
            limiter.reserve("127.0.0.1", "other5@example.com")
        self.now += timedelta(seconds=120)
        limiter.reserve("127.0.0.1", "other5@example.com")

    def test_spoofed_headers_cannot_bypass_ip_limit(self):
        for i in range(30):
            self.login(email=f"user{i}@example.com")
        self.assertEqual(self.login(email="fresh@example.com", headers={
            "X-Forwarded-For": "198.51.100.2", "X-Real-IP": "198.51.100.3", "CF-Connecting-IP": "198.51.100.4",
        })[0], 429)

    def test_store_failure_does_not_run_password_check(self):
        with patch("app.core.login_rate_limit.reserve", side_effect=RuntimeError("internal")), patch("app.routers.auth.verify_password_and_update") as verify:
            status, body, headers = self.login(email="good@example.com")
        self.assertEqual(status, 503)
        self.assertEqual(headers["retry-after"], "1")
        self.assertNotIn("internal", str(body))
        verify.assert_not_called()

    def test_atomic_ip_concurrency_across_independent_accounts(self):
        from app.core import login_rate_limit as limiter
        def reserve(i):
            try:
                return limiter.reserve("127.0.0.1", f"account{i}@example.com")
            except limiter.Limited:
                return None
        with ThreadPoolExecutor(max_workers=8) as pool:
            reservations = list(pool.map(reserve, range(8)))
        self.assertEqual(sum(item is not None for item in reservations), 4)

    def test_malformed_payload_retains_422_and_is_request_limited(self):
        with patch("app.routers.auth.verify_password_and_update") as verify:
            for _ in range(60):
                self.assertEqual(asgi_request(self.app, "POST", "/auth/login", {"email": "invalid"})[0], 422)
            self.assertEqual(asgi_request(self.app, "POST", "/auth/login", {})[0], 429)
            verify.assert_not_called()

    def test_config_rejects_invalid_limits(self):
        from app.core.login_rate_limit import Policy
        import os
        for value in ("0", "-1", "invalid", "10001"):
            with patch.dict(os.environ, {"LOGIN_RATE_ACCOUNT_FAILURES": value}):
                with self.assertRaises(RuntimeError):
                    Policy.from_env()

    def test_known_account_block_prevents_password_work(self):
        for _ in range(5):
            self.assertEqual(self.login(email="good@example.com")[0], 401)
        with patch("app.routers.auth.verify_password_and_update") as verify:
            self.assertEqual(self.login(email="good@example.com", password="correct-password")[0], 429)
            verify.assert_not_called()

    def test_double_failure_returns_generic_503_but_cancellation_propagates(self):
        import asyncio
        from unittest.mock import AsyncMock, Mock
        from app.core import login_rate_limit as limiter
        request = Mock()
        request.json = AsyncMock(return_value={"email": "good@example.com", "senha": "wrong"})
        with patch.object(limiter, "get_client_ip", return_value="127.0.0.1"), patch.object(limiter, "reserve", return_value=1), patch.object(limiter, "finish", side_effect=RuntimeError("private-store-error")):
            response = asyncio.run(limiter.limit_login(request, AsyncMock(side_effect=RuntimeError("private-route-error")), Mock()))
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.headers["retry-after"], "1")
            self.assertNotIn(b"private", response.body)
            with self.assertRaises(asyncio.CancelledError):
                asyncio.run(limiter.limit_login(request, AsyncMock(side_effect=asyncio.CancelledError()), Mock()))
