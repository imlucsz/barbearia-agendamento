import bcrypt
import unittest

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.security import decode_access_token, get_password_hash, verify_password
from app.models.user import RoleEnum, User


class AuthenticationRegressionTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.application = load_app_for_environment("test").app

    def add_user(self, email, password_hash):
        db = main.SessionLocal()
        try:
            user = User(
                nome="Authentication Regression",
                email=email,
                senha_hash=password_hash,
                role=RoleEnum.CLIENTE,
                consentimento_lgpd=True,
            )
            db.add(user)
            db.commit()
            return user.id
        finally:
            db.close()

    def test_argon2_hash_login_issues_a_valid_hs256_access_token(self):
        password_hash = get_password_hash("correct-password")
        self.assertTrue(password_hash.startswith("$argon2id$"))
        self.add_user("argon@example.com", password_hash)

        status, body = asgi_request(
            self.application, "POST", "/auth/login",
            {"email": "argon@example.com", "senha": "correct-password"},
        )

        self.assertEqual(status, 200, body)
        self.assertEqual(body["token_type"], "bearer")
        self.assertEqual(decode_access_token(body["access_token"])["sub"], "argon@example.com")

    def test_legacy_bcrypt_hash_logs_in_and_is_upgraded_to_argon2(self):
        legacy_hash = bcrypt.hashpw(b"legacy-password", bcrypt.gensalt(rounds=12)).decode("ascii")
        self.assertTrue(legacy_hash.startswith(("$2a$", "$2b$")))
        user_id = self.add_user("legacy@example.com", legacy_hash)

        status, body = asgi_request(
            self.application, "POST", "/auth/login",
            {"email": "legacy@example.com", "senha": "legacy-password"},
        )

        self.assertEqual(status, 200, body)
        db = main.SessionLocal()
        try:
            updated = db.query(User).filter(User.id == user_id).one().senha_hash
        finally:
            db.close()
        self.assertTrue(updated.startswith("$argon2id$"))
        self.assertTrue(verify_password("legacy-password", updated))

    def test_incorrect_password_does_not_upgrade_or_accept_a_legacy_hash(self):
        legacy_hash = bcrypt.hashpw(b"legacy-password", bcrypt.gensalt(rounds=12)).decode("ascii")
        user_id = self.add_user("wrong-password@example.com", legacy_hash)

        status, _body = asgi_request(
            self.application, "POST", "/auth/login",
            {"email": "wrong-password@example.com", "senha": "incorrect-password"},
        )

        self.assertEqual(status, 401)
        db = main.SessionLocal()
        try:
            stored = db.query(User).filter(User.id == user_id).one().senha_hash
        finally:
            db.close()
        self.assertEqual(stored, legacy_hash)

    def test_unknown_or_malformed_hash_fails_authentication_without_server_error(self):
        self.add_user("malformed@example.com", "not-a-supported-password-hash")

        status, body = asgi_request(
            self.application, "POST", "/auth/login",
            {"email": "malformed@example.com", "senha": "any-password"},
        )

        self.assertEqual(status, 401)
        self.assertEqual(body["detail"], "Email ou senha incorretos")


if __name__ == "__main__":
    unittest.main()
