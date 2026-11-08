"""Real PostgreSQL constraints and concurrent HTTP registrations, no mocked DB."""
import os
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError
from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.email_identity import is_email_conflict, normalize_email
from app.models.user import User
from app.schemas.user import EsqueciSenhaRequest


@unittest.skipUnless(os.environ.get("BOOKING_TEST_BACKEND") == "postgresql", "Requires disposable PostgreSQL harness")
class EmailIdentityPostgresTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("test").app

    def test_index_constraint_and_encoding_metadata(self):
        with main.engine.connect() as connection:
            encoding, collate, ctype = connection.execute(text("SELECT pg_encoding_to_char(encoding), datcollate, datctype FROM pg_database WHERE datname=current_database()" )).one()
            index = connection.execute(text("SELECT i.indisunique, pg_get_indexdef(i.indexrelid) FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=current_schema() AND c.relname='uq_users_email_identity'" )).one()
            sql_encoding = connection.execute(text("SHOW client_encoding")).scalar_one()
            self.assertEqual(encoding, "UTF8")
            self.assertTrue(index[0])
            self.assertIn("lower(ltrim(rtrim(email)))", index[1].replace("(email)::text", "email"))
            print(json.dumps({"email_test_metadata": {"server_encoding":encoding, "client_encoding":sql_encoding,
                "driver_encoding":connection.connection.driver_connection.info.encoding,
                "server_version":connection.connection.driver_connection.info.server_version,
                "collation":collate,"ctype":ctype,"unique_functional_index":bool(index[0])}}))

    def test_real_constraint_rejects_ascii_equivalence_and_maps_metadata(self):
        with main.engine.begin() as connection:
            connection.execute(text("INSERT INTO users (nome,email,senha_hash,consentimento_lgpd) VALUES ('Fixture',' Raw@EXAMPLE.COM ','fixture',false)"))
        with main.engine.connect() as connection:
            transaction = connection.begin()
            with self.assertRaises(IntegrityError) as caught:
                connection.execute(text("INSERT INTO users (nome,email,senha_hash,consentimento_lgpd) VALUES ('Fixture','raw@example.com','fixture',false)"))
            self.assertTrue(is_email_conflict(caught.exception))
            self.assertEqual(caught.exception.orig.sqlstate, "23505")
            self.assertEqual(caught.exception.orig.diag.constraint_name, "uq_users_email_identity")
            transaction.rollback()

    def test_two_simultaneous_registrations_resolve_real_unique_conflict(self):
        for first, second in [(" Race@EXAMPLE.COM ", "race@example.com"), ("Jose\u0301@example.com", "JOSÉ@EXAMPLE.COM")]:
            barrier = Barrier(2)
            backend_pids = set()
            canonical = EsqueciSenhaRequest(email=first).email
            def after_lookup(_connection, _cursor, statement, parameters, _context, _many):
                if statement.lstrip().upper().startswith("SELECT") and "FROM users" in statement and isinstance(parameters, dict) and canonical in parameters.values():
                    backend_pids.add(_connection.connection.driver_connection.info.backend_pid)
                    barrier.wait(timeout=15)
            def register(value):
                return asgi_request(self.app, "POST", "/auth/register", {
                    "nome":"Fixture", "email":value, "senha":"fixture-password", "consentimento_lgpd":True,
                })
            event.listen(main.engine, "after_cursor_execute", after_lookup)
            try:
                with ThreadPoolExecutor(max_workers=2) as executor:
                    results = list(executor.map(register, [first, second]))
            finally:
                event.remove(main.engine, "after_cursor_execute", after_lookup)
            self.assertEqual(sorted(status for status, _ in results), [201, 409])
            self.assertEqual(len(backend_pids), 2)
            failure = next(body for status, body in results if status == 409)
            self.assertEqual(failure, {"detail":"E-mail já cadastrado"})
            with main.SessionLocal() as db:
                self.assertEqual(db.query(User).filter(User.email == canonical).count(), 1)

    def test_current_c_collation_does_not_guarantee_full_unicode_canonical_identity(self):
        with main.engine.connect() as connection:
            ctype = connection.execute(text("SELECT datctype FROM pg_database WHERE datname=current_database()" )).scalar_one()
        if ctype not in {"C", "POSIX"}:
            self.skipTest("Characterization targets the executor's explicit C locale")
        # Bypass application normalization deliberately, only on disposable data.
        with main.engine.begin() as connection:
            connection.execute(text("INSERT INTO users (nome,email,senha_hash,consentimento_lgpd) VALUES ('Fixture',:email,'fixture',false)"), {"email":"josé@example.com"})
            connection.execute(text("INSERT INTO users (nome,email,senha_hash,consentimento_lgpd) VALUES ('Fixture',:email,'fixture',false)"), {"email":"JOSÉ@example.com"})
            connection.execute(text("INSERT INTO users (nome,email,senha_hash,consentimento_lgpd) VALUES ('Fixture',:email,'fixture',false)"), {"email":"jose\u0301@example.com"})
        with main.SessionLocal() as db:
            self.assertEqual(db.query(User).count(), 3)
        self.assertTrue(normalize_email("JOSÉ@example.com") == "josé@example.com")

    def test_sql_trim_does_not_remove_unicode_whitespace_like_python_strip(self):
        raw = "\u00a0person@example.com\u00a0"
        with main.engine.begin() as connection:
            connection.execute(text("INSERT INTO users (nome,email,senha_hash,consentimento_lgpd) VALUES ('Fixture',:email,'fixture',false)"), {"email":raw})
            connection.execute(text("INSERT INTO users (nome,email,senha_hash,consentimento_lgpd) VALUES ('Fixture','person@example.com','fixture',false)"))
            sql_key = connection.execute(text("SELECT lower(ltrim(rtrim(:email)))"), {"email":raw}).scalar_one()
        self.assertTrue(sql_key == raw)
        self.assertTrue(normalize_email(raw) == "person@example.com")
        with main.SessionLocal() as db:
            self.assertEqual(db.query(User).count(), 2)
