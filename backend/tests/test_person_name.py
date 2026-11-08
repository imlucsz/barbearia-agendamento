import unittest
import unicodedata

from pydantic import ValidationError
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserLogin, EsqueciSenhaRequest,
    RedefinirSenhaRequest, PasswordConfirmation,
)


class PersonNameTests(unittest.TestCase):
    def create(self, name):
        return UserCreate(nome=name, email="fixture@example.com", senha="fixture-only", consentimento_lgpd=True)

    def test_nfd_is_normalized_to_nfc_in_create_and_update(self):
        name = "Jose\u0301"
        self.assertEqual(self.create(name).nome, "José")
        self.assertEqual(UserUpdate(nome=name).nome, "José")

    def test_unicode_separators_are_collapsed_and_trimmed(self):
        name = " \u00a0Ana  Maria\u2003\u202fda Silva\u3000 "
        expected = "Ana Maria da Silva"
        self.assertEqual(self.create(name).nome, expected)
        self.assertEqual(UserUpdate(nome=name).nome, expected)

    def test_international_names_and_format_characters_are_preserved(self):
        for name in ["João", "Ana-Maria", "D'Ávila", "O’Connor", "李 明", "محمد", "अर्जुन", "Prince", "علی\u200cرضا", "क्\u200dष", "A\u2060B"]:
            with self.subTest(name=name):
                self.assertEqual(self.create(name).nome, unicodedata.normalize("NFC", name))

    def test_invisible_only_and_blank_names_are_rejected(self):
        for name in ["", "   ", "\u00a0", "\u200b", "\ufeff", "\u200c\u200d", "\u2060", "\u034f", "\ufe0f", "\U000e0100", "\u115f\u1160", "\u3164", "\uffa0", "\u2800", " \u200b\ufeff "]:
            with self.subTest(codepoints=[hex(ord(c)) for c in name]):
                for make in [self.create, lambda value: UserUpdate(nome=value)]:
                    with self.assertRaises(ValidationError):
                        make(name)

    def test_controls_and_invalid_unicode_are_rejected_before_space_collapse(self):
        for name in ["Ana\nMaria", "Ana\tMaria", "A\x00B", "A\x7fB", "A\x85B", "A\ud800B"]:
            for make in [self.create, lambda value: UserUpdate(nome=value)]:
                with self.assertRaises(ValidationError):
                    make(name)

    def test_length_is_checked_after_normalization(self):
        self.assertEqual(len(self.create("e\u0301" * 120).nome), 120)
        self.assertEqual(self.create(" " * 100 + "A" * 120 + " " * 100).nome, "A" * 120)
        with self.assertRaises(ValidationError):
            self.create("A" * 121)
        with self.assertRaises(ValidationError):
            UserUpdate(nome="e\u0301" * 121)

    def test_excessive_raw_input_is_rejected_even_if_it_would_normalize_short(self):
        with self.assertRaises(ValidationError):
            self.create(" " * 4096 + "A")

    def test_partial_update_and_explicit_null_keep_previous_semantics(self):
        self.assertEqual(UserUpdate().model_dump(exclude_unset=True), {})
        self.assertEqual(UserUpdate(bloqueado=True).model_dump(exclude_unset=True), {"bloqueado": True})
        with self.assertRaises(ValidationError):
            UserUpdate(nome=None)
        for invalid in [12, True, [], {}]:
            with self.assertRaises(ValidationError):
                self.create(invalid)

    def test_response_does_not_normalize_existing_names(self):
        legacy = "Jose\u0301  da Silva"
        response = UserResponse(id=1, nome=legacy, email="fixture@example.com", role="cliente")
        self.assertEqual(response.nome, legacy)

    def test_normalization_is_idempotent(self):
        once = self.create("  Jose\u0301  da Silva ").nome
        self.assertEqual(self.create(once).nome, once)

    def test_email_and_secret_fields_keep_exact_previous_behavior(self):
        email = "  Mixed+tag@Example.COM  "
        for schema, extra in [
            (UserCreate, {"nome": "Ana", "senha": "  fixture-only  ", "consentimento_lgpd": True}),
            (UserUpdate, {}), (UserLogin, {"senha": "  fixture-only  "}), (EsqueciSenhaRequest, {}),
        ]:
            value = schema(email=email, **extra)
            self.assertTrue(value.email == "mixed+tag@example.com")
            if hasattr(value, "senha"):
                self.assertTrue(value.senha == "fixture-only")
        self.assertTrue(RedefinirSenhaRequest(token="  fixture-token  ", nova_senha="  fixture-only  ").nova_senha == "fixture-only")
        self.assertTrue(PasswordConfirmation(senha_atual="  fixture-only  ").senha_atual == "fixture-only")
        self.assertTrue(UserLogin(email="jose\u0301@example.com", senha="fixture-only").email == "josé@example.com")
