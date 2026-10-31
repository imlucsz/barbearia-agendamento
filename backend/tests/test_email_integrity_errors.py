import sqlite3
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from sqlalchemy.exc import IntegrityError
from support import asgi_request, load_app_for_environment, main, reset_database
from app.database import get_db
from app.models.user import User, RoleEnum
from app.core.security import create_access_token, get_password_hash
from app.core.email_identity import is_email_conflict


def unique_error(message="UNIQUE constraint failed: users.email", code=2067):
    original = sqlite3.IntegrityError(message)
    original.sqlite_errorcode = code
    return IntegrityError("test-only", {}, original)


class EmailIntegrityTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("test").app
        self.db = main.SessionLocal()
        self.admin = User(nome="Admin teste", email="admin@example.com", senha_hash=get_password_hash("test-only-password"), role=RoleEnum.ADMIN)
        self.client = User(nome="Cliente teste", email="client@example.com", senha_hash=get_password_hash("test-only-password"), role=RoleEnum.CLIENTE)
        self.db.add_all([self.admin,self.client])
        self.db.commit()
        self.client_id = self.client.id
        self.headers = {"Authorization": "Bearer " + create_access_token({"sub":self.admin.email})}
        self.app.dependency_overrides[get_db] = lambda: self.db

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.db.close()

    def test_register_race_returns_conflict_only_for_known_email_constraint(self):
        for error, expected in [(unique_error(),409),(unique_error("NOT NULL constraint failed: users.nome",1299),None)]:
            with patch.object(self.db,"flush",side_effect=error):
                if expected:
                    code,_ = asgi_request(self.app,"POST","/auth/register",payload={"nome":"Novo","email":"new@example.com","senha":"test-only-password","consentimento_lgpd":True})
                    self.assertEqual(code,expected)
                else:
                    with self.assertRaises(IntegrityError):
                        asgi_request(self.app,"POST","/auth/register",payload={"nome":"Novo","email":"new@example.com","senha":"test-only-password","consentimento_lgpd":True})

    def test_admin_commit_race_is_controlled_without_hiding_other_integrity_errors(self):
        for error, expected in [(unique_error(),409),(unique_error("UNIQUE constraint failed: other.value"),None)]:
            with patch.object(self.db,"commit",side_effect=error):
                if expected:
                    code,_ = asgi_request(self.app,"PUT",f"/users/{self.client_id}",payload={"email":"new@example.com"},headers=self.headers)
                    self.assertEqual(code,expected)
                else:
                    with self.assertRaises(IntegrityError):
                        asgi_request(self.app,"PUT",f"/users/{self.client_id}",payload={"email":"new@example.com"},headers=self.headers)

    def test_postgres_constraint_metadata_is_required(self):
        error = SimpleNamespace(orig=SimpleNamespace(sqlstate="23505",diag=SimpleNamespace(table_name="users",constraint_name="uq_users_email_identity")))
        self.assertTrue(is_email_conflict(error))
        error.orig.diag.constraint_name = "unrelated_constraint"
        self.assertFalse(is_email_conflict(error))
        error.orig.diag.constraint_name = "uq_users_email_identity"
        error.orig.sqlstate = "23502"
        self.assertFalse(is_email_conflict(error))

    def test_real_unique_violation_after_another_registration_wins(self):
        self.assertIsNone(self.db.query(User.id).filter(User.email == "race@example.com").first())
        with main.SessionLocal() as winner:
            winner.add(User(nome="Vencedor",email="race@example.com",senha_hash="test-only-not-a-password-hash",role=RoleEnum.CLIENTE))
            winner.commit()
        self.db.add(User(nome="Concorrente",email="RACE@example.com",senha_hash="test-only-not-a-password-hash",role=RoleEnum.CLIENTE))
        with self.assertRaises(IntegrityError) as caught:
            self.db.flush()
        self.assertTrue(is_email_conflict(caught.exception))
        self.db.rollback()
        self.assertEqual(self.db.query(User).filter(User.email == "race@example.com").count(),1)
