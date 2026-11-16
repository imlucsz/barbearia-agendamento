"""Password confirmations outside login are rate limited and never take login capacity."""
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from fastapi import HTTPException

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core import password_confirmation_limit, security
from app.core.clock import utc_now_naive
from app.models.user import LoginAttempt, RoleEnum, User

PASSWORD = "fixture-confirmation-password"


class PasswordConfirmationLaneTests(unittest.TestCase):
    def setUp(self):
        for name in ("_password_verification_slots", "_password_confirmation_slots"):
            slots = patch.object(security, name, threading.BoundedSemaphore(1))
            slots.start()
            self.addCleanup(slots.stop)

    def test_busy_confirmation_does_not_take_login_capacity(self):
        entered, release = threading.Event(), threading.Event()

        def work(_plain, stored):
            if stored == "confirmation-hash":
                entered.set()
                if not release.wait(10):
                    raise AssertionError("Confirmation release timed out")
            return True, None

        with patch.object(security.password_hash, "verify_and_update", side_effect=work):
            with ThreadPoolExecutor(max_workers=1) as pool:
                pending = pool.submit(security.verify_password_confirmation, "fixture", "confirmation-hash")
                try:
                    self.assertTrue(entered.wait(10))
                    self.assertEqual(security.verify_password_and_update("fixture", "login-hash"), (True, None))
                    with self.assertRaises(HTTPException) as busy:
                        security.verify_password_confirmation("fixture", "confirmation-hash")
                    self.assertEqual(busy.exception.status_code, 503)
                    self.assertEqual(busy.exception.headers["Retry-After"], "1")
                finally:
                    release.set()
                self.assertTrue(pending.result(timeout=15))


class AccountErasureConfirmationLimitTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("test").app
        self.first_id = self.add_user("confirm-a@example.com")
        self.second_id = self.add_user("confirm-b@example.com")

    def add_user(self, email):
        db = main.SessionLocal()
        try:
            user = User(nome="Conta Ficticia", email=email, senha_hash=security.get_password_hash(PASSWORD),
                        role=RoleEnum.CLIENTE, consentimento_lgpd=True, consentimento_em=utc_now_naive())
            db.add(user)
            db.commit()
            return user.id
        finally:
            db.close()

    def token(self, user_id):
        return security.create_access_token({"sub": str(user_id)})

    def erase(self, user_id, password, client_ip="127.0.0.1"):
        return asgi_request(self.app, "DELETE", "/users/me", {"senha_atual": password},
                            headers={"Authorization": f"Bearer {self.token(user_id)}"},
                            return_headers=True, client_ip=client_ip)

    def is_active(self, user_id):
        db = main.SessionLocal()
        try:
            return db.get(User, user_id).ativo
        finally:
            db.close()

    def test_account_failures_are_limited_across_ips(self):
        maximum = password_confirmation_limit.settings().rate_limit_max_attempts
        statuses = [self.erase(self.first_id, "wrong-fixture", f"198.51.100.{index}")[0]
                    for index in range(1, maximum + 1)]
        self.assertEqual(statuses, [403] * maximum)
        with patch.object(security.password_hash, "verify_and_update") as verify:
            status, body, headers = self.erase(self.first_id, PASSWORD, "203.0.113.9")
        verify.assert_not_called()
        self.assertEqual(status, 429, body)
        self.assertGreaterEqual(int(headers["retry-after"]), 1)
        self.assertTrue(self.is_active(self.first_id))
        self.assertEqual(self.erase(self.second_id, PASSWORD, "203.0.113.9")[0], 200)

    def test_ip_failures_are_limited_across_accounts(self):
        maximum = password_confirmation_limit.settings().rate_limit_max_attempts
        for index in range(maximum):
            user_id = self.first_id if index % 2 == 0 else self.second_id
            self.assertEqual(self.erase(user_id, "wrong-fixture", "192.0.2.10")[0], 403)
        with patch.object(security.password_hash, "verify_and_update") as verify:
            self.assertEqual(self.erase(self.second_id, PASSWORD, "192.0.2.10")[0], 429)
        verify.assert_not_called()
        self.assertEqual(self.erase(self.second_id, PASSWORD, "192.0.2.11")[0], 200)

    def test_saturated_confirmation_is_not_counted_as_failure(self):
        lane = threading.BoundedSemaphore(1)
        lane.acquire()
        try:
            with patch.object(security, "_password_confirmation_slots", lane):
                status, body, headers = self.erase(self.first_id, "wrong-fixture")
        finally:
            lane.release()
        self.assertEqual(status, 503, body)
        self.assertEqual(headers["retry-after"], "1")
        db = main.SessionLocal()
        try:
            self.assertEqual(db.query(LoginAttempt).filter(
                LoginAttempt.rota == password_confirmation_limit.ACCOUNT_ERASURE_PATH).count(), 0)
        finally:
            db.close()

    def test_login_succeeds_while_erasure_confirmation_runs(self):
        entered, release = threading.Event(), threading.Event()
        original = security.password_hash.verify_and_update
        calls = 0
        mutex = threading.Lock()

        def gated(plain, stored):
            nonlocal calls
            with mutex:
                calls += 1
                first = calls == 1
            if first:
                entered.set()
                if not release.wait(10):
                    raise AssertionError("Confirmation release timed out")
            return original(plain, stored)

        with patch.object(security, "_password_verification_slots", threading.BoundedSemaphore(1)), \
                patch.object(security.password_hash, "verify_and_update", side_effect=gated):
            with ThreadPoolExecutor(max_workers=1) as pool:
                erasure = pool.submit(self.erase, self.first_id, "wrong-fixture", "198.51.100.50")
                try:
                    self.assertTrue(entered.wait(10))
                    status, body = asgi_request(self.app, "POST", "/auth/login",
                                                {"email": "confirm-b@example.com", "senha": PASSWORD},
                                                client_ip="198.51.100.60")
                    self.assertEqual(status, 200, body)
                finally:
                    release.set()
                self.assertEqual(erasure.result(timeout=15)[0], 403)


if __name__ == "__main__":
    unittest.main()
