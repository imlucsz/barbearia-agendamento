"""Characterize the current contract without changing normalization policy."""
import unittest
from unittest.mock import patch

from pydantic import ValidationError
from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.security import create_access_token, get_password_hash
from app.models.user import User, RoleEnum, PasswordResetToken
from app.schemas.user import UserCreate, UserUpdate, UserLogin, EsqueciSenhaRequest


class EmailIdentityContractTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("test").app

    def register(self, email):
        return asgi_request(self.app, "POST", "/auth/register", {
            "nome": "Fixture", "email": email, "senha": "  fixture-password  ", "consentimento_lgpd": True,
        })

    def test_all_input_schemas_agree_on_current_equivalence(self):
        pairs = [
            ("  MIXED+tag@Example.COM  ", "mixed+tag@example.com"),
            ("Jose\u0301@EXAMPLE.COM", "josé@example.com"),
            ("Person@xn--bcher-kva.de", "person@bücher.de"),
            ("\u00a0person@example.com\u00a0", "person@example.com"),
        ]
        for value, expected in pairs:
            for schema, extras in [(UserCreate, {"nome": "Fixture", "senha": "fixture-password", "consentimento_lgpd": True}),
                                   (UserUpdate, {}), (UserLogin, {"senha": "fixture-password"}), (EsqueciSenhaRequest, {})]:
                with self.subTest(schema=schema.__name__, case=pairs.index((value, expected))):
                    self.assertTrue(schema(email=value, **extras).email == expected)

    def test_invalid_addresses_are_rejected_in_each_input_schema(self):
        for value in ["bad@@example.com", "a b@example.com", "", "a\x00@example.com", "a\n@example.com"]:
            for schema, extras in [(UserCreate, {"nome": "Fixture", "senha": "fixture-password", "consentimento_lgpd": True}),
                                   (UserUpdate, {}), (UserLogin, {"senha": "fixture-password"}), (EsqueciSenhaRequest, {})]:
                with self.assertRaises(ValidationError):
                    schema(email=value, **extras)

    def test_equivalent_registration_login_and_recovery_use_one_identity(self):
        for index, (first, equivalent) in enumerate([
            (" Mixed+tag@Example.COM ", "MIXED+TAG@example.com"),
            ("Jose\u0301@example.com", "JOSÉ@EXAMPLE.COM"),
            ("Person@xn--bcher-kva.de", "person@bücher.de"),
        ]):
            self.assertEqual(self.register(first)[0], 201)
            duplicate, body = self.register(equivalent)
            self.assertEqual(duplicate, 400)  # Existing pre-check contract, not a race.
            self.assertEqual(set(body), {"detail"})
            status, _ = asgi_request(self.app, "POST", "/auth/login", {"email": equivalent, "senha": "  fixture-password  "}, client_ip=f"192.0.2.{index+1}")
            self.assertEqual(status, 200)
            with patch("app.routers.auth.send_password_reset_email") as sender:
                # Each case is a distinct actor; do not exhaust main's IP limiter.
                ip = f"198.51.100.{index + 1}"
                first_response = asgi_request(self.app, "POST", "/auth/esqueci-senha", {"email": first}, client_ip=ip)
                unknown_response = asgi_request(self.app, "POST", "/auth/esqueci-senha", {"email": f"unknown{index}@example.com"}, client_ip=ip)
            self.assertEqual(first_response[0], 200)
            self.assertEqual(first_response, unknown_response)
            self.assertEqual(sender.call_count, 1)
            expected_recipient = ["mixed+tag@example.com", "josé@example.com", "person@bücher.de"][index]
            self.assertTrue(sender.call_args.args[0] == expected_recipient)
        with main.SessionLocal() as db:
            self.assertEqual(db.query(User).count(), 3)

    def test_aliases_dots_and_casefold_variants_remain_distinct(self):
        for value in ["first.last@example.com", "firstlast@example.com", "first.last+tag@example.com",
                      "straße@example.com", "strasse@example.com"]:
            self.assertEqual(self.register(value)[0], 201)
        with main.SessionLocal() as db:
            self.assertEqual(db.query(User).count(), 5)

    def test_recovery_finds_each_equivalent_input_as_the_first_request(self):
        cases = [
            ("  MIXED+tag@Example.COM  ", "mixed+tag@example.com"),
            ("Jose\u0301@EXAMPLE.COM", "josé@example.com"),
            ("Person@xn--bcher-kva.de", "person@bücher.de"),
            ("\u00a0person@example.com\u00a0", "person@example.com"),
        ]
        for index, (variant, canonical) in enumerate(cases):
            for supplied in (variant, canonical):
                with self.subTest(case=index, input_is_canonical=supplied == canonical):
                    # Both spellings must resolve as first requests on fresh fixtures.
                    # This characterizes identity, not repeated-send suppression.
                    reset_database()
                    self.app = load_app_for_environment("test").app
                    with main.SessionLocal() as db:
                        row = User(nome="Fixture", email=canonical, senha_hash="fixture")
                        db.add(row)
                        db.commit()
                        user_id = row.id
                    with patch("app.routers.auth.send_password_reset_email") as sender:
                        known = asgi_request(self.app, "POST", "/auth/esqueci-senha", {"email": supplied})
                        unknown = asgi_request(self.app, "POST", "/auth/esqueci-senha", {"email": f"unknown{index}@example.com"})
                    self.assertEqual(known[0], 200)
                    self.assertEqual(known, unknown)
                    sender.assert_called_once()
                    self.assertTrue(sender.call_args.args[0] == canonical)
                    with main.SessionLocal() as db:
                        reset = db.query(PasswordResetToken).filter_by(user_id=user_id).one()
                        self.assertFalse(reset.used)

    def test_admin_duplicate_update_is_safe_and_preserves_original_credentials(self):
        with main.SessionLocal() as db:
            admin = User(nome="Admin", email="admin@example.com", senha_hash="fixture", role=RoleEnum.ADMIN)
            client = User(nome="Client", email="client@example.com", senha_hash=get_password_hash("fixture-password"))
            db.add_all([admin, client, User(nome="Other", email="josé@example.com", senha_hash="fixture")])
            db.commit()
            user_id, original_hash = client.id, client.senha_hash
        headers = {"Authorization": "Bearer " + create_access_token({"sub": "admin@example.com"})}
        status, body = asgi_request(self.app, "PUT", f"/users/{user_id}", {"email": "Jose\u0301@EXAMPLE.COM"}, headers=headers)
        self.assertEqual(status, 409)
        self.assertEqual(body, {"detail": "E-mail já cadastrado"})
        status, _ = asgi_request(self.app, "PUT", f"/users/{user_id}", {"email": " CLIENT@EXAMPLE.COM "}, headers=headers)
        self.assertEqual(status, 200)
        with main.SessionLocal() as db:
            row = db.query(User).filter_by(id=user_id).one()
            self.assertTrue(row.email == "client@example.com" and row.senha_hash == original_hash)

    def test_legacy_orm_decomposed_identity_is_not_rewritten_or_found_by_nfc_login(self):
        # A characterization of a known gap: ORM lower/strip is not EmailStr NFC.
        legacy = "jose\u0301@example.com"
        with main.SessionLocal() as db:
            row = User(nome="Legacy", email=legacy, senha_hash=get_password_hash("fixture-password"))
            db.add(row)
            db.commit()
            original_hash = row.senha_hash
        status, _ = asgi_request(self.app, "POST", "/auth/login", {"email": legacy, "senha": "fixture-password"})
        self.assertEqual(status, 401)
        with patch("app.routers.auth.send_password_reset_email") as sender:
            known = asgi_request(self.app, "POST", "/auth/esqueci-senha", {"email": legacy})
            unknown = asgi_request(self.app, "POST", "/auth/esqueci-senha", {"email": "unknown@example.com"})
        self.assertEqual(known, unknown)
        sender.assert_not_called()
        with main.SessionLocal() as db:
            row = db.query(User).one()
            self.assertTrue(row.email == legacy and row.senha_hash == original_hash)

    def test_email_partial_update_semantics_and_successful_identity_change(self):
        self.assertEqual(UserUpdate().model_dump(exclude_unset=True), {})
        self.assertEqual(UserUpdate(nome="Fixture").model_dump(exclude_unset=True), {"nome":"Fixture"})
        with self.assertRaises(ValidationError):
            UserUpdate(email=None)
        with main.SessionLocal() as db:
            admin = User(nome="Admin", email="admin@example.com", senha_hash="fixture", role=RoleEnum.ADMIN)
            client = User(nome="Client", email="old@example.com", senha_hash=get_password_hash("fixture-password"))
            db.add_all([admin, client])
            db.commit()
            user_id, original_hash = client.id, client.senha_hash
        headers = {"Authorization": "Bearer " + create_access_token({"sub":"admin@example.com"})}
        status, _ = asgi_request(self.app, "PUT", f"/users/{user_id}", {"nome":"Updated"}, headers=headers)
        self.assertEqual(status, 200)
        with main.SessionLocal() as db:
            row = db.query(User).filter_by(id=user_id).one()
            self.assertTrue(row.email == "old@example.com" and row.senha_hash == original_hash)
        value = " Jose\u0301@xn--bcher-kva.de "
        expected = "josé@bücher.de"
        status, _ = asgi_request(self.app, "PUT", f"/users/{user_id}", {"email":value}, headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(asgi_request(self.app, "POST", "/auth/login", {"email":value,"senha":"fixture-password"})[0], 200)
        self.assertEqual(asgi_request(self.app, "POST", "/auth/login", {"email":"old@example.com","senha":"fixture-password"})[0], 401)
        with patch("app.routers.auth.send_password_reset_email") as sender:
            self.assertEqual(asgi_request(self.app,"POST","/auth/esqueci-senha",{"email":value}),
                             asgi_request(self.app,"POST","/auth/esqueci-senha",{"email":"old@example.com"}))
        self.assertEqual(sender.call_count, 1)
        self.assertTrue(sender.call_args.args[0] == expected)
        with main.SessionLocal() as db:
            row = db.query(User).filter_by(id=user_id).one()
            self.assertTrue(row.email == expected and row.senha_hash == original_hash)
