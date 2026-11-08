"""F2 transaction boundary regressions, using the isolated test harness."""
# ruff: noqa: I001
# Initialize the test database through support before application imports.
import unittest
from unittest.mock import patch

import test_f2_login_resilience as fixtures
from support import main

from app.models.user import LoginAttempt, RefreshToken
from app.routers import auth


class F2TransactionTests(unittest.TestCase):
    setUp = fixtures.F2LoginResilienceTests.setUp
    login = fixtures.F2LoginResilienceTests.login

    def test_failure_after_refresh_flush_before_commit_rolls_back_claim_and_session(self):
        original = auth._new_refresh_token

        def fail(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError('controlled precommit failure')

        with patch.object(auth, '_new_refresh_token', side_effect=fail):
            status, _, headers = self.login()
        self.assertEqual(status, 503)
        self.assertNotIn('set-cookie', headers)
        with main.SessionLocal() as db:
            self.assertEqual(db.query(RefreshToken).count(), 0)
            row = db.query(LoginAttempt).one()
            self.assertEqual(row.resultado, 'neutro')
            self.assertFalse(row.em_andamento)

    def test_commit_failure_does_not_publish_committed_marker(self):
        original_claim = auth.claim_login_reservation
        session_class = main.SessionLocal.class_
        original_commit = session_class.commit

        def claim(db, request):
            result = original_claim(db, request)
            db.info['f2_fail_commit'] = True
            return result

        def commit(db):
            if db.info.pop('f2_fail_commit', False):
                raise RuntimeError('controlled commit failure')
            return original_commit(db)

        with patch.object(auth, 'claim_login_reservation', side_effect=claim), \
                patch.object(session_class, 'commit', commit):
            status, _, headers = self.login()
        self.assertEqual(status, 503)
        self.assertNotIn('set-cookie', headers)
        with main.SessionLocal() as db:
            self.assertEqual(db.query(RefreshToken).count(), 0)
            self.assertEqual(db.query(LoginAttempt).one().resultado, 'neutro')

    def test_failure_after_confirmed_commit_cannot_roll_back_session(self):
        # A later response-construction/transport failure is not a second DB transaction.
        with patch.object(auth, '_set_refresh_cookie', side_effect=RuntimeError('postcommit failure')), \
                patch('app.core.login_rate_limit.finish') as finish:
            status, _, _ = self.login()
        self.assertEqual(status, 503)
        finish.assert_not_called()
        with main.SessionLocal() as db:
            self.assertEqual(db.query(RefreshToken).count(), 1)
            self.assertEqual(db.query(LoginAttempt).one().resultado, 'sucesso')
