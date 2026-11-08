import hashlib
import json
import os
import unittest
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from datetime import timedelta
from unittest.mock import patch

from support import asgi_request, load_app_for_environment, main, reset_database
from fastapi import FastAPI
from app.core.security import get_password_hash, verify_password
from app.models.user import PasswordResetToken, User
from app.core.clock import utc_now_naive
from app.core.email import send_password_reset_email
from app.config import settings as load_settings
from app.core.password_reset_limits import reserve_request, finish_reservation, prune_expired
from app.models.user import PasswordResetLimit
from sqlalchemy.exc import OperationalError
from password_reset_process_worker import reserve_in_process


def asgi_post(application, path, payload):
    return asgi_request(application, "POST", path, payload)


class PasswordResetTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app_module = load_app_for_environment("development")
        self.application = self.app_module.app
        self.assertIsInstance(self.application, FastAPI)
        self.assertIs(self.application, self.app_module.app)
        self.assertEqual(self.app_module.APP_ENV, "development")
        for key in (
            "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM",
            "PASSWORD_RESET_URL",
        ):
            os.environ.pop(key, None)
        os.environ["SMTP_PORT"] = "587"

    def create_user(self, email, password="old-password"):
        db = main.SessionLocal()
        try:
            user = User(
                nome=email.split("@")[0],
                email=email,
                senha_hash=get_password_hash(password),
                consentimento_lgpd=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user.id
        finally:
            db.close()

    def reset_token_count(self, user_id=None):
        db = main.SessionLocal()
        try:
            query = db.query(PasswordResetToken)
            if user_id is not None:
                query = query.filter(PasswordResetToken.user_id == user_id)
            return query.count()
        finally:
            db.close()

    def test_ten_quick_requests_preserve_first_link_and_uniform_response(self):
        self.create_user("known@example.com")
        with patch("app.routers.auth.send_password_reset_email") as sender:
            responses = [asgi_post(self.application, "/auth/esqueci-senha", {
                "email": "KNOWN@example.com" if index % 2 else "known@example.com",
            }) for index in range(10)]
        self.assertTrue(all(response == responses[0] for response in responses))
        self.assertEqual(responses[0][0], 200)
        self.assertEqual(sender.call_count, 1)
        self.assertEqual(self.reset_token_count(), 1)
        status, _ = asgi_post(self.application, "/auth/redefinir-senha", {
            "token": sender.call_args.args[1], "nova_senha": "new-password",
        })
        self.assertEqual(status, 200)

    def test_cooldown_across_ips_and_request_allowed_at_sixty_seconds(self):
        self.create_user("known@example.com")
        now = utc_now_naive()
        with patch("app.routers.auth.utc_now_naive", return_value=now) as clock, patch(
            "app.routers.auth.send_password_reset_email"
        ) as sender:
            for index in range(4):
                status, _ = asgi_request(self.application, "POST", "/auth/esqueci-senha",
                    {"email": "known@example.com"}, client_ip=f"192.0.2.{index + 1}")
                self.assertEqual(status, 200)
            self.assertEqual(sender.call_count, 1)
            clock.return_value = now + timedelta(seconds=59)
            asgi_post(self.application, "/auth/esqueci-senha", {"email": "known@example.com"})
            self.assertEqual(sender.call_count, 1)
            clock.return_value = now + timedelta(seconds=60)
            asgi_post(self.application, "/auth/esqueci-senha", {"email": "known@example.com"})
            self.assertEqual(sender.call_count, 2)

    def test_simultaneous_requests_from_independent_sessions_send_once(self):
        self.create_user("known@example.com")
        def request(index):
            return asgi_request(self.application, "POST", "/auth/esqueci-senha",
                {"email": "known@example.com"}, client_ip=f"192.0.2.{index + 1}")
        with patch("app.routers.auth.send_password_reset_email") as sender:
            with ThreadPoolExecutor(max_workers=6) as executor:
                responses = list(executor.map(request, range(10)))
        self.assertTrue(all(response == responses[0] for response in responses))
        self.assertEqual(responses[0][0], 200)
        self.assertEqual(sender.call_count, 1)
        self.assertEqual(self.reset_token_count(), 1)

    def test_account_limit_applies_across_ips_and_expires(self):
        self.create_user("known@example.com")
        now = utc_now_naive()
        with patch.dict(os.environ, {"PASSWORD_RESET_ACCOUNT_MAX_REQUESTS": "2"}), patch(
            "app.routers.auth.utc_now_naive", return_value=now
        ) as clock, patch("app.routers.auth.send_password_reset_email") as sender:
            for index in range(3):
                clock.return_value = now + timedelta(seconds=60 * index)
                self.assertEqual(asgi_request(self.application, "POST", "/auth/esqueci-senha",
                    {"email": "known@example.com"}, client_ip=f"192.0.2.{index + 1}")[0], 200)
            self.assertEqual(sender.call_count, 2)
            clock.return_value = now + timedelta(hours=1)
            asgi_post(self.application, "/auth/esqueci-senha", {"email": "known@example.com"})
            self.assertEqual(sender.call_count, 3)

    def test_ip_limit_covers_different_existing_and_unknown_accounts(self):
        for index in range(3):
            self.create_user(f"person{index}@example.com")
        with patch.dict(os.environ, {"PASSWORD_RESET_IP_MAX_REQUESTS": "2"}), patch(
            "app.routers.auth.send_password_reset_email"
        ) as sender:
            responses = [asgi_post(self.application, "/auth/esqueci-senha", {"email": email})
                for email in ["unknown@example.com", "person0@example.com", "person1@example.com", "person2@example.com"]]
        self.assertTrue(all(response == responses[0] for response in responses))
        self.assertEqual(responses[0][0], 200)
        self.assertEqual(sender.call_count, 1)

    def test_failed_delivery_preserves_previous_link_and_reserves_cooldown(self):
        self.create_user("known@example.com")
        now = utc_now_naive()
        with patch("app.routers.auth.utc_now_naive", return_value=now) as clock, patch(
            "app.routers.auth.send_password_reset_email"
        ) as sender:
            original = asgi_post(self.application, "/auth/esqueci-senha", {"email": "known@example.com"})
            first_token = sender.call_args.args[1]
            clock.return_value = now + timedelta(seconds=60)
            sender.side_effect = TimeoutError("simulated delivery timeout")
            failed = asgi_post(self.application, "/auth/esqueci-senha", {"email": "known@example.com"})
            repeated = asgi_post(self.application, "/auth/esqueci-senha", {"email": "known@example.com"})
            self.assertEqual(original, failed)
            self.assertEqual(failed, repeated)
            self.assertEqual(sender.call_count, 2)
            self.assertEqual(self.reset_token_count(), 1)
            with main.SessionLocal() as db:
                stored = db.query(PasswordResetToken).one()
                self.assertFalse(stored.used)
                self.assertEqual(stored.token, hashlib.sha256(first_token.encode()).hexdigest())
            clock.return_value = now + timedelta(seconds=120)
            sender.side_effect = None
            self.assertEqual(asgi_post(self.application, "/auth/esqueci-senha", {"email": "known@example.com"}), original)
            self.assertEqual(sender.call_count, 3)

    def test_configurable_cooldown_and_unknown_account_are_indistinguishable(self):
        self.create_user("known@example.com")
        now = utc_now_naive()
        with patch.dict(os.environ, {"PASSWORD_RESET_COOLDOWN_SECONDS": "90"}), patch(
            "app.routers.auth.utc_now_naive", return_value=now
        ) as clock, patch("app.routers.auth.send_password_reset_email") as sender:
            responses = [asgi_post(self.application, "/auth/esqueci-senha", {"email": email})
                for email in ["known@example.com", "unknown@example.com", "known@example.com", "unknown@example.com"]]
            self.assertTrue(all(response == responses[0] for response in responses))
            clock.return_value = now + timedelta(seconds=60)
            asgi_post(self.application, "/auth/esqueci-senha", {"email": "known@example.com"})
            self.assertEqual(sender.call_count, 1)
            clock.return_value = now + timedelta(seconds=90)
            asgi_post(self.application, "/auth/esqueci-senha", {"email": "known@example.com"})
            self.assertEqual(sender.call_count, 2)

    def test_sender_still_running_after_cooldown_does_not_allow_second_send(self):
        self.create_user("known@example.com")
        entered, release = Event(), Event()
        now = utc_now_naive()
        def slow_sender(*_args):
            entered.set()
            if not release.wait(10):
                raise TimeoutError("test synchronization timed out")
        with patch("app.routers.auth.utc_now_naive", return_value=now) as clock, patch(
            "app.routers.auth.send_password_reset_email", side_effect=slow_sender
        ) as sender, ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(asgi_post, self.application, "/auth/esqueci-senha", {"email": "known@example.com"})
            try:
                self.assertTrue(entered.wait(5))
                clock.return_value = now + timedelta(seconds=61)
                second = asgi_request(self.application, "POST", "/auth/esqueci-senha",
                    {"email": "known@example.com"}, client_ip="192.0.2.50")
                self.assertEqual(second[0], 200)
                self.assertEqual(sender.call_count, 1)
            finally:
                release.set()
            self.assertEqual(first.result(timeout=5), second)

    def test_abandoned_lease_expires_and_old_owner_cannot_release_new_reservation(self):
        configured, now = load_settings(), utc_now_naive()
        with main.SessionLocal() as db:
            original = reserve_request(db, "known@example.com", "192.0.2.1", now, configured)
            self.assertIsNotNone(original)
            self.assertIsNone(reserve_request(db, "known@example.com", "192.0.2.2", now + timedelta(seconds=61), configured))
            later = now + timedelta(seconds=8 * configured.smtp_timeout_seconds + 61)
            renewed = reserve_request(db, "known@example.com", "192.0.2.3", later, configured)
            self.assertIsNotNone(renewed)
            self.assertFalse(finish_reservation(db, original, later))
            self.assertTrue(finish_reservation(db, renewed, later))
            db.commit()

    def test_expired_limit_rows_are_pruned_without_deleting_current_reservations(self):
        configured, now = load_settings(), utc_now_naive()
        with main.SessionLocal() as db:
            reserve_request(db, "old@example.com", "192.0.2.1", now - timedelta(hours=3), configured)
            current = reserve_request(db, "current@example.com", "192.0.2.2", now, configured)
            prune_expired(db, now, configured)
            db.commit()
            self.assertEqual(db.query(PasswordResetLimit).count(), 2)
            self.assertIsNotNone(db.query(PasswordResetLimit).filter_by(key=current[0]).first())
            self.assertTrue(all("@" not in row.key and "192.0.2" not in row.key for row in db.query(PasswordResetLimit)))

    def test_database_admission_failure_fails_closed_without_email_or_secret(self):
        self.create_user("known@example.com")
        with patch("app.routers.auth.reserve_request", side_effect=OperationalError("private SQL", {}, Exception())), patch(
            "app.routers.auth.send_password_reset_email"
        ) as sender:
            response = asgi_post(self.application, "/auth/esqueci-senha", {"email": "known@example.com"})
        self.assertEqual(response[0], 200)
        self.assertNotIn("private", json.dumps(response))
        sender.assert_not_called()

    def test_four_processes_compete_for_one_real_database_reservation(self):
        context = multiprocessing.get_context("spawn")
        barrier, results = context.Barrier(4), context.Queue()
        url = main.engine.url.render_as_string(hide_password=False)
        now = utc_now_naive()
        processes = [context.Process(target=reserve_in_process, args=(
            url, "parallel@example.com", f"192.0.2.{index + 1}", now, barrier, results,
        )) for index in range(4)]
        try:
            for process in processes:
                process.start()
            outcomes = [results.get(timeout=35) for _ in processes]
            self.assertTrue(all(state == "ok" for state, _ in outcomes), outcomes)
            self.assertEqual(sum(bool(accepted) for _, accepted in outcomes), 1)
            for process in processes:
                process.join(timeout=10)
                self.assertEqual(process.exitcode, 0)
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=5)
            results.close()

    def test_late_sender_cannot_invalidate_newer_link_and_login_still_works(self):
        self.create_user("known@example.com")
        entered, release = Event(), Event()
        tokens = []
        now = utc_now_naive()
        configured = load_settings()
        def sender(_recipient, token):
            tokens.append(token)
            if len(tokens) == 1:
                entered.set()
                if not release.wait(10):
                    raise TimeoutError("test synchronization timed out")
        with patch("app.routers.auth.utc_now_naive", return_value=now) as clock, patch(
            "app.routers.auth.send_password_reset_email", side_effect=sender
        ), ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(asgi_post, self.application, "/auth/esqueci-senha", {"email": "known@example.com"})
            try:
                self.assertTrue(entered.wait(5))
                clock.return_value = now + timedelta(seconds=8 * configured.smtp_timeout_seconds + 61)
                second = asgi_request(self.application, "POST", "/auth/esqueci-senha",
                    {"email": "known@example.com"}, client_ip="192.0.2.60")
                self.assertEqual(second[0], 200)
                self.assertEqual(len(tokens), 2)
            finally:
                release.set()
            self.assertEqual(first.result(timeout=5), second)
        with main.SessionLocal() as db:
            self.assertEqual(db.query(PasswordResetToken).one().token, hashlib.sha256(tokens[1].encode()).hexdigest())
        self.assertEqual(asgi_post(self.application, "/auth/redefinir-senha",
            {"token": tokens[0], "nova_senha": "wrong-new-password"})[0], 400)
        self.assertEqual(asgi_post(self.application, "/auth/redefinir-senha",
            {"token": tokens[1], "nova_senha": "new-password"})[0], 200)
        self.assertEqual(asgi_post(self.application, "/auth/login",
            {"email": "known@example.com", "senha": "new-password"})[0], 200)

    def test_recovery_response_is_uniform_and_contains_no_secret(self):
        self.create_user("known@example.com")
        with patch("app.routers.auth.send_password_reset_email") as sender:
            known_status, known_body = asgi_post(
                self.application, "/auth/esqueci-senha", {"email": "known@example.com"}
            )
            unknown_status, unknown_body = asgi_post(
                self.application, "/auth/esqueci-senha", {"email": "unknown@example.com"}
            )

        self.assertEqual((known_status, known_body), (unknown_status, unknown_body))
        self.assertNotIn("dev_token", known_body)
        self.assertNotIn("reset.html", json.dumps(known_body))
        self.assertEqual(sender.call_count, 1)
        raw_token = sender.call_args.args[1]
        self.assertNotIn(raw_token, json.dumps(known_body))

        db = main.SessionLocal()
        try:
            stored = db.query(PasswordResetToken).one()
            self.assertEqual(stored.token, hashlib.sha256(raw_token.encode()).hexdigest())
            self.assertNotEqual(stored.token, raw_token)
        finally:
            db.close()

    def test_invalid_and_expired_tokens_are_rejected(self):
        user_id = self.create_user("person@example.com")
        expired_token = "expired-reset-token"
        db = main.SessionLocal()
        try:
            db.add(PasswordResetToken(
                user_id=user_id,
                token=hashlib.sha256(expired_token.encode()).hexdigest(),
                expires_at=utc_now_naive() - timedelta(seconds=1),
                used=False,
            ))
            db.commit()
        finally:
            db.close()

        invalid_status, _ = asgi_post(
            self.application, "/auth/redefinir-senha",
            {"token": "not-a-token", "nova_senha": "new-password"},
        )
        expired_status, _ = asgi_post(
            self.application, "/auth/redefinir-senha",
            {"token": expired_token, "nova_senha": "new-password"},
        )
        self.assertEqual(invalid_status, 400)
        self.assertEqual(expired_status, 400)

    def test_only_valid_token_changes_its_account_and_token_cannot_be_reused(self):
        account_a = self.create_user("a@example.com", "old-password-a")
        account_b = self.create_user("b@example.com", "old-password-b")
        with patch("app.routers.auth.send_password_reset_email") as sender:
            asgi_post(self.application, "/auth/esqueci-senha", {"email": "a@example.com"})
        token = sender.call_args.args[1]

        status, body = asgi_post(
            self.application, "/auth/redefinir-senha",
            {"token": token, "nova_senha": "new-password-a"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["mensagem"], "Senha redefinida com sucesso")

        retry_status, _ = asgi_post(
            self.application, "/auth/redefinir-senha",
            {"token": token, "nova_senha": "attacker-password"},
        )
        self.assertEqual(retry_status, 400)

        db = main.SessionLocal()
        try:
            updated_a = db.query(User).filter(User.id == account_a).one()
            unchanged_b = db.query(User).filter(User.id == account_b).one()
            self.assertTrue(verify_password("new-password-a", updated_a.senha_hash))
            self.assertFalse(verify_password("attacker-password", updated_a.senha_hash))
            self.assertTrue(verify_password("old-password-b", unchanged_b.senha_hash))
        finally:
            db.close()

    def test_failed_email_delivery_returns_generic_response_and_persists_no_token(self):
        user_id = self.create_user("known@example.com")
        with patch(
            "app.routers.auth.send_password_reset_email",
            side_effect=RuntimeError("mail unavailable"),
        ):
            status, body = asgi_post(
                self.application, "/auth/esqueci-senha", {"email": "known@example.com"}
            )

        self.assertEqual(status, 200)
        self.assertEqual(body, {"mensagem": "Se o email existir, um link de redefinição foi gerado."})
        self.assertEqual(self.reset_token_count(user_id), 0)

    def test_test_or_production_environment_has_no_local_email_fallback(self):
        user_id = self.create_user("known@example.com")
        for app_env in (None, "production"):
            with self.subTest(app_env=app_env):
                app_module = load_app_for_environment(app_env)
                application = app_module.app
                self.assertIsInstance(application, FastAPI)
                self.assertIs(application, app_module.app)
                self.assertEqual(app_module.APP_ENV, app_env or "test")
                with patch("logging.Logger.info") as logger_info:
                    status, body = asgi_post(
                        application, "/auth/esqueci-senha",
                        {"email": "known@example.com"},
                    )
                self.assertEqual(status, 200)
                self.assertNotIn("dev_token", body)
                self.assertEqual(self.reset_token_count(user_id), 0)
                logger_info.assert_not_called()

    def test_validation_errors_do_not_echo_password_or_reset_token(self):
        secret_input = "xP@ss"
        status, body = asgi_post(
            self.application,
            "/auth/redefinir-senha",
            {"token": "private-reset-token", "nova_senha": secret_input},
        )

        self.assertEqual(status, 422)
        serialized = json.dumps(body)
        self.assertNotIn(secret_input, serialized)
        self.assertNotIn("private-reset-token", serialized)
        self.assertNotIn('"input"', serialized)
        self.assertNotIn('"ctx"', serialized)
        self.assertIn("loc", body["detail"][0])

    def test_password_reset_link_keeps_token_in_fragment_not_query(self):
        settings = {
            "APP_ENV": "development",
            "SMTP_HOST": "smtp.example.test",
            "SMTP_PORT": "587",
            "SMTP_FROM": "barbearia@example.test",
            "PASSWORD_RESET_URL": "https://frontend.example/reset.html?campaign=dev&token=old#previous",
            "SMTP_USERNAME": "",
            "SMTP_PASSWORD": "",
        }
        with patch.dict(os.environ, settings), patch("app.core.email.smtplib.SMTP") as smtp_factory:
            send_password_reset_email("client@example.test", "test-reset-token")

        smtp = smtp_factory.return_value.__enter__.return_value
        message = smtp.send_message.call_args.args[0]
        body = message.get_content()
        link = next(line for line in body.splitlines() if line.startswith("https://"))
        self.assertIn("?campaign=dev#token=test-reset-token", link)
        self.assertNotIn("token=old", link)
        self.assertNotIn("&token=test-reset-token", link)

    def test_explicit_development_without_smtp_does_not_log_or_persist_token(self):
        user_id = self.create_user("local@example.com")
        with patch("logging.Logger.info") as logger_info:
            status, body = asgi_post(
                self.application, "/auth/esqueci-senha", {"email": "local@example.com"}
            )

        self.assertEqual(status, 200)
        self.assertNotIn("dev_token", body)
        self.assertEqual(self.reset_token_count(user_id), 0)
        logger_info.assert_not_called()


if __name__ == "__main__":
    unittest.main()
