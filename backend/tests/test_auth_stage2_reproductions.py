"""Deterministic regressions for distributed admission and session revocation."""
import os
import threading
import unittest
from contextvars import ContextVar
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from dataclasses import replace
from unittest.mock import patch

from support import asgi_request, load_app_for_environment, main, reset_database
from test_auth_sessions import cookie_token
from app.core.security import get_password_hash
from app.core import security
from app.models.user import User, RoleEnum
from app.routers import auth


class Stage2Reproductions(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment('test').app
        self.environment = patch.dict(os.environ, {
            'CLIENT_IP_SOURCE': 'direct', 'CORS_ALLOWED_ORIGINS': 'https://frontend.test.invalid',
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        db = main.SessionLocal()
        try:
            db.add(User(nome='Conta Ficticia', email='stage2@example.com',
                        senha_hash=get_password_hash('fixture-password-only'),
                        role=RoleEnum.CLIENTE, consentimento_lgpd=True))
            db.add(User(nome='Outra Conta Ficticia', email='victim@example.com',
                        senha_hash=get_password_hash('fixture-other-password-only'),
                        role=RoleEnum.CLIENTE, consentimento_lgpd=True))
            db.commit()
        finally:
            db.close()

    def login(self, email='stage2@example.com', password='fixture-password-only'):
        return asgi_request(self.app, 'POST', '/auth/login',
                            {'email': email, 'senha': password}, return_headers=True)

    def session_request(self, endpoint, raw):
        return asgi_request(self.app, 'POST', '/auth/' + endpoint, headers={
            'Cookie': 'refresh_token=' + raw, 'Origin': 'https://frontend.test.invalid',
        }, return_headers=True)

    def test_other_account_success_cannot_reset_victim_failure_budget(self):
        for _ in range(4):
            self.assertEqual(self.login('victim@example.com', 'invalid-fixture')[0], 401)
        self.assertEqual(self.login()[0], 200)
        # Five total failures against victim, with another account's success between.
        self.login('victim@example.com', 'invalid-fixture')
        status, _, _ = self.login('victim@example.com', 'invalid-fixture')
        self.assertEqual(status, 429, 'Another account success reset victim failure budget')

    def test_concurrent_admission_limits_password_checks_before_results(self):
        admitted = 0
        lock = threading.Lock()
        reached = threading.Event()
        release = threading.Event()
        original = auth.verify_password_and_update
        def gate(password, stored):
            nonlocal admitted
            with lock:
                admitted += 1
                if admitted == 2:
                    reached.set()
            if not release.wait(10):
                raise AssertionError('Controlled release timed out')
            return original(password, stored)
        from app.core import login_rate_limit
        policy = replace(login_rate_limit.POLICY, account_failures=2)
        # Isolate distributed admission at two from the default local capacity of one.
        with patch.object(login_rate_limit, 'POLICY', policy), \
                patch.object(security, '_password_verification_slots', threading.BoundedSemaphore(2)), \
                patch('app.routers.auth.verify_password_and_update', side_effect=gate):
            with ThreadPoolExecutor(max_workers=3) as pool:
                futures = [pool.submit(self.login, password='invalid-fixture') for _ in range(3)]
                try:
                    self.assertTrue(reached.wait(10), 'Admitted requests did not reach gate')
                finally:
                    release.set()
                results = [future.result(timeout=20)[0] for future in futures]
        self.assertTrue(all(status in (401, 429) for status in results))
        self.assertLessEqual(admitted, 2, 'Concurrent requests exceeded password-check budget')

    def test_logout_revokes_successor_even_when_rotation_response_is_late(self):
        status, _, headers = self.login()
        self.assertEqual(status, 200)
        first = cookie_token(headers)
        committed = threading.Event()
        release = threading.Event()
        original = auth._set_refresh_cookie
        def gate(response, token):
            if token is not None:
                committed.set()
                if not release.wait(15):
                    raise AssertionError('Controlled refresh release timed out')
            return original(response, token)
        with patch('app.routers.auth._set_refresh_cookie', side_effect=gate):
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self.session_request, 'refresh', first)
                try:
                    self.assertTrue(committed.wait(15), 'Refresh did not commit rotation')
                    self.assertEqual(self.session_request('logout', first)[0], 200)
                finally:
                    release.set()
                status, _, rotated_headers = future.result(timeout=20)
        self.assertEqual(status, 200)
        successor = cookie_token(rotated_headers)
        self.assertEqual(self.session_request('refresh', successor)[0], 401,
                         'Successor remained renewable after logout')

    def test_logout_commits_before_waiting_refresh_acquires_lock(self):
        status, _, headers = self.login()
        self.assertEqual(status, 200)
        first = cookie_token(headers)
        reached = threading.Event()
        release = threading.Event()
        original = auth._lock_refresh_user
        is_refresh = ContextVar('stage2_refresh_gate', default=False)
        def gate(db, user_id):
            if is_refresh.get():
                reached.set()
                if not release.wait(15):
                    raise AssertionError('Controlled lock release timed out')
            return original(db, user_id)
        def refresh_worker():
            is_refresh.set(True)
            return self.session_request('refresh', first)
        with patch('app.routers.auth._lock_refresh_user', side_effect=gate):
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(refresh_worker)
                try:
                    self.assertTrue(reached.wait(15))
                    self.assertEqual(self.session_request('logout', first)[0], 200)
                finally:
                    release.set()
                status, body, response_headers = future.result(timeout=20)
        self.assertEqual(status, 401)
        self.assertFalse('access_token' in body)
        self.assertFalse('set-cookie' in response_headers)

    def test_logout_revokes_only_its_family(self):
        _, _, first = self.login()
        _, _, independent = self.login()
        self.assertEqual(self.session_request('logout', cookie_token(first))[0], 200)
        self.assertEqual(self.session_request('refresh', cookie_token(first))[0], 401)
        self.assertEqual(self.session_request('refresh', cookie_token(independent))[0], 200)

    def test_reset_revokes_rotated_successor_before_late_response(self):
        status, _, headers = self.login()
        self.assertEqual(status, 200)
        first = cookie_token(headers)
        with patch('app.routers.auth.send_password_reset_email') as delivery:
            self.assertEqual(asgi_request(self.app, 'POST', '/auth/esqueci-senha', {'email': 'stage2@example.com'})[0], 200)
        reset_token = delivery.call_args.args[1]
        committed = threading.Event()
        release = threading.Event()
        original = auth._set_refresh_cookie
        def gate(response, token):
            committed.set()
            if not release.wait(15):
                raise AssertionError('Controlled reset release timed out')
            return original(response, token)
        with patch('app.routers.auth._set_refresh_cookie', side_effect=gate):
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self.session_request, 'refresh', first)
                try:
                    self.assertTrue(committed.wait(15))
                    self.assertEqual(asgi_request(self.app, 'POST', '/auth/redefinir-senha', {
                        'token': reset_token, 'nova_senha': 'fixture-replacement-password',
                    })[0], 200)
                finally:
                    release.set()
                status, _, rotated = future.result(timeout=20)
        self.assertEqual(status, 200)
        self.assertEqual(self.session_request('refresh', cookie_token(rotated))[0], 401)
        self.assertEqual(self.login(password='fixture-replacement-password')[0], 200)

    def test_characterize_access_token_lifetime_after_logout(self):
        status, body, headers = self.login()
        self.assertEqual(status, 200)
        authorization = {'Authorization': 'Bearer ' + body['access_token']}
        self.assertEqual(self.session_request('logout', cookie_token(headers))[0], 200)
        self.assertEqual(asgi_request(self.app, 'GET', '/auth/me', headers=authorization)[0], 200)
        future = datetime.now(timezone.utc) + timedelta(minutes=61)
        class ExpiredClock(datetime):
            @classmethod
            def now(cls, tz=None):
                return future if tz else future.replace(tzinfo=None)
        with patch('jwt.api_jwt.datetime', ExpiredClock):
            self.assertEqual(asgi_request(self.app, 'GET', '/auth/me', headers=authorization)[0], 401)

    def test_characterize_access_token_lifetime_after_reset(self):
        status, body, headers = self.login()
        self.assertEqual(status, 200)
        authorization = {'Authorization': 'Bearer ' + body['access_token']}
        with patch('app.routers.auth.send_password_reset_email') as delivery:
            self.assertEqual(asgi_request(self.app, 'POST', '/auth/esqueci-senha', {'email': 'stage2@example.com'})[0], 200)
        status, _ = asgi_request(self.app, 'POST', '/auth/redefinir-senha', {
            'token': delivery.call_args.args[1], 'nova_senha': 'fixture-after-reset-password',
        })
        self.assertEqual(status, 200)
        self.assertEqual(self.session_request('refresh', cookie_token(headers))[0], 401)
        self.assertEqual(asgi_request(self.app, 'GET', '/auth/me', headers=authorization)[0], 200)
        future = datetime.now(timezone.utc) + timedelta(minutes=61)
        class ExpiredClock(datetime):
            @classmethod
            def now(cls, tz=None):
                return future if tz else future.replace(tzinfo=None)
        with patch('jwt.api_jwt.datetime', ExpiredClock):
            self.assertEqual(asgi_request(self.app, 'GET', '/auth/me', headers=authorization)[0], 401)
