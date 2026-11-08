"""Bounded PostgreSQL-only F2 connection and refresh regressions."""
# ruff: noqa: I001
# support configures the disposable database before app imports.
import os
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from sqlalchemy import create_engine, text
from support import main
import test_auth_stage2_reproductions as fixtures
from test_auth_sessions import cookie_token
from app.models.user import LoginAttempt, RefreshToken, User
from app.routers import auth

EVIDENCE = {}


@unittest.skipUnless(os.environ.get('BOOKING_TEST_BACKEND') == 'postgresql',
                     'PostgreSQL disposable harness required')
class F2PostgreSQLTests(unittest.TestCase):
    setUp = fixtures.Stage2Reproductions.setUp
    login = fixtures.Stage2Reproductions.login
    session_request = fixtures.Stage2Reproductions.session_request

    def test_login_connection_loss_before_commit_rolls_back_session_and_claim(self):
        original = auth.record_audit
        killed = []

        def disconnect(db, request, **kwargs):
            if kwargs.get('acao') == 'auth.login':
                pid = db.execute(text('SELECT pg_backend_pid()')).scalar_one()
                killer_engine = create_engine(main.engine.url, hide_parameters=True)
                try:
                    with killer_engine.connect() as killer:
                        self.assertTrue(killer.execute(text('SELECT pg_terminate_backend(:pid)'),
                                                       {'pid': pid}).scalar_one())
                finally:
                    killer_engine.dispose()
                killed.append(pid)
            return original(db, request, **kwargs)

        with patch.object(auth, 'record_audit', side_effect=disconnect):
            status, _, headers = self.login()
        with main.SessionLocal() as db:
            rows = db.query(LoginAttempt).all()
            evidence = {'status': status, 'cookie_issued': 'set-cookie' in headers,
                        'refresh_count': db.query(RefreshToken).count(),
                        'attempt_outcomes': [r.resultado for r in rows],
                        'pending_attempts': sum(r.em_andamento for r in rows),
                        'terminated_owned_backend_count': len(killed)}
            EVIDENCE['login_precommit_disconnect'] = evidence
            self.assertEqual(status, 503)
            self.assertNotIn('set-cookie', headers)
            self.assertEqual(evidence['refresh_count'], 0)
            self.assertEqual(evidence['attempt_outcomes'], ['neutro'])
            self.assertEqual(evidence['pending_attempts'], 0)
        self.assertEqual(self.login()[0], 200)

    def test_simultaneous_rotation_rechecks_after_real_user_lock_wait(self):
        for repetition in range(3):
            status, _, headers = self.login()
            self.assertEqual(status, 200)
            raw = cookie_token(headers)
            barrier = threading.Barrier(2, timeout=8)
            has_lock = threading.Event()
            release = threading.Event()
            original = auth._lock_refresh_user
            pids = []
            mutex = threading.Lock()

            def gate(db, user_id, *, mutex=mutex, pids=pids, barrier=barrier,
                     original=original, has_lock=has_lock, release=release):
                pid = db.execute(text('SELECT pg_backend_pid()')).scalar_one()
                with mutex:
                    pids.append(pid)
                barrier.wait()
                original(db, user_id)
                has_lock.set()
                if not release.wait(10):
                    raise AssertionError('Controlled lock holder release timed out')

            with patch.object(auth, '_lock_refresh_user', side_effect=gate), \
                    ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(self.session_request, 'refresh', raw) for _ in range(2)]
                try:
                    self.assertTrue(has_lock.wait(8))
                    waited = False
                    deadline = time.monotonic() + 5
                    with main.engine.connect() as observer:
                        while time.monotonic() < deadline:
                            # PostgreSQL may cache activity snapshots within a transaction.
                            observer.execute(text('SELECT pg_stat_clear_snapshot()'))
                            waited = observer.execute(text(
                                "SELECT count(*) FROM pg_stat_activity WHERE pid IN (:a,:b) "
                                "AND wait_event_type='Lock'"), {'a': pids[0], 'b': pids[1]}).scalar_one() == 1
                            if waited:
                                break
                            time.sleep(0.05)
                    self.assertTrue(waited, 'No real PostgreSQL lock wait observed')
                finally:
                    release.set()
                results = [f.result(timeout=15) for f in futures]
            self.assertEqual(len(set(pids)), 2)
            self.assertCountEqual([r[0] for r in results], [200, 401])
            successor = cookie_token(next(r[2] for r in results if r[0] == 200))
            self.assertEqual(self.session_request('refresh', successor)[0], 401)
            with main.SessionLocal() as db:
                rows = db.query(RefreshToken).all()
                self.assertEqual(len(rows), (repetition + 1) * 2)
                self.assertTrue(all(row.revoked_at is not None for row in rows))
                ids = {row.id for row in rows}
                self.assertTrue(all(row.replaced_by_id is None or row.replaced_by_id in ids for row in rows))
                self.assertEqual(db.query(User).count(), 2)
        EVIDENCE['simultaneous_rotation'] = {'repetitions': 3, 'statuses_each': [200, 401],
            'tokens_per_family': 2, 'all_revoked_after_replay': True, 'distinct_backend_sessions': True,
            'pg_stat_activity_lock_wait_observed_each_repetition': True}
