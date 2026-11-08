"""Local CPU capacity survives cancelled waiters and distributed lease expiry."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import Mock, patch

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core import security, login_rate_limit
from app.core.clock import utc_now_naive
from app.models.user import User, RefreshToken, LoginAttempt
from app.routers import auth
from app.schemas.user import UserLogin


class PasswordCapacityTests(unittest.TestCase):
    def setUp(self):
        slots = patch.object(security, '_password_verification_slots', threading.BoundedSemaphore(1))
        slots.start()
        self.addCleanup(slots.stop)

    def test_all_verification_consumers_reject_immediately_while_upgrade_runs(self):
        entered, release = threading.Event(), threading.Event()
        calls = 0

        def upgrade(_plain, _stored):
            nonlocal calls
            calls += 1
            if calls == 1:
                entered.set()
                if not release.wait(10):
                    raise AssertionError('Upgrade release timed out')
            return True, 'fixture-upgraded-hash'

        with patch.object(security.password_hash, 'verify_and_update', side_effect=upgrade):
            with ThreadPoolExecutor(max_workers=1) as pool:
                pending = pool.submit(security.verify_password_and_update, 'fixture', 'fixture-hash')
                try:
                    self.assertTrue(entered.wait(10))
                    # A timed-out waiter does not stop the synchronous upgrade.
                    with self.assertRaises(TimeoutError):
                        pending.result(timeout=0)
                    for verify in (security.verify_password, security.verify_password_and_update):
                        with self.assertRaises(HTTPException) as blocked:
                            verify('fixture', 'fixture-hash')
                        self.assertEqual(blocked.exception.status_code, 503)
                        self.assertEqual(blocked.exception.headers['Retry-After'], '1')
                    # Unknown identities receive the same overload response.
                    with self.assertRaises(HTTPException):
                        security.verify_password_and_update('fixture', None)
                finally:
                    release.set()
                self.assertEqual(pending.result(timeout=15), (True, 'fixture-upgraded-hash'))
        self.assertEqual(calls, 1)

    def test_multiple_threads_obey_configured_capacity(self):
        entered, release = threading.Event(), threading.Event()
        mutex = threading.Lock()
        calls = 0

        def work(_plain, _stored):
            nonlocal calls
            with mutex:
                calls += 1
                ordinal = calls
                if calls == 2:
                    entered.set()
            if ordinal <= 2 and not release.wait(10):
                raise AssertionError('Parallel work release timed out')
            return True, None

        def verify():
            try:
                security.verify_password_and_update('fixture', 'fixture-hash')
                return 200
            except HTTPException as error:
                return error.status_code

        with patch.object(security, '_password_verification_slots', threading.BoundedSemaphore(2)), \
                patch.object(security.password_hash, 'verify_and_update', side_effect=work):
            with ThreadPoolExecutor(max_workers=8) as pool:
                first = [pool.submit(verify) for _ in range(2)]
                try:
                    self.assertTrue(entered.wait(10))
                    extra = [pool.submit(verify) for _ in range(6)]
                    self.assertEqual([future.result(timeout=5) for future in extra], [503] * 6)
                finally:
                    release.set()
                self.assertEqual([future.result(timeout=15) for future in first], [200, 200])
        self.assertEqual(calls, 2)

    def test_execution_error_is_generic_and_releases_capacity(self):
        with patch.object(security.password_hash, 'verify_and_update', side_effect=RuntimeError('internal-fixture')):
            with self.assertRaises(HTTPException) as failed:
                security.verify_password_and_update('fixture', 'fixture-hash')
        self.assertEqual(failed.exception.status_code, 503)
        self.assertNotIn('internal-fixture', failed.exception.detail)
        with patch.object(security.password_hash, 'verify_and_update', return_value=(True, None)):
            self.assertTrue(security.verify_password('fixture', 'fixture-hash'))

    def test_limit_configuration_is_validated(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(security._load_password_verification_limit(), 1)
        for value in ('0', '-1', '17', 'invalid'):
            with patch.dict(os.environ, {'AUTH_PASSWORD_MAX_CONCURRENCY': value}):
                with self.assertRaises(RuntimeError):
                    security._load_password_verification_limit()
        with patch.dict(os.environ, {'AUTH_PASSWORD_MAX_CONCURRENCY': '2'}):
            self.assertEqual(security._load_password_verification_limit(), 2)


class LoginCapacityLifecycleTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment('test').app
        environment = patch.dict(os.environ, {'CLIENT_IP_SOURCE': 'direct'})
        environment.start()
        self.addCleanup(environment.stop)
        slots = patch.object(security, '_password_verification_slots', threading.BoundedSemaphore(1))
        slots.start()
        self.addCleanup(slots.stop)
        db = main.SessionLocal()
        try:
            self.original_hash = security.get_password_hash('fixture-capacity-password')
            db.add(User(nome='Conta Ficticia', email='capacity@example.com',
                        senha_hash=self.original_hash,
                        consentimento_lgpd=True))
            db.commit()
        finally:
            db.close()

    def login(self, email='capacity@example.com'):
        return asgi_request(self.app, 'POST', '/auth/login', {
            'email': email, 'senha': 'fixture-capacity-password',
        }, return_headers=True)

    def assert_no_session(self):
        db = main.SessionLocal()
        try:
            self.assertEqual(db.query(RefreshToken).count(), 0)
        finally:
            db.close()

    def test_expired_successful_result_does_not_create_session(self):
        now = utc_now_naive()
        entered, release = threading.Event(), threading.Event()
        upgraded = security.get_password_hash('fixture-capacity-password')

        def work(_plain, _stored):
            entered.set()
            if not release.wait(10):
                raise AssertionError('Expired work release timed out')
            return True, upgraded

        with patch.object(login_rate_limit, 'utc_now_naive', side_effect=lambda: now), \
                patch.object(security.password_hash, 'verify_and_update', side_effect=work):
            with ThreadPoolExecutor(max_workers=1) as pool:
                pending = pool.submit(self.login)
                try:
                    self.assertTrue(entered.wait(10))
                    now += timedelta(seconds=login_rate_limit.POLICY.lease_seconds + 1)
                finally:
                    release.set()
                status, body, headers = pending.result(timeout=15)
        self.assertEqual(status, 503)
        self.assertNotIn('access_token', body)
        self.assertNotIn('set-cookie', headers)
        self.assert_no_session()
        db = main.SessionLocal()
        try:
            self.assertTrue(db.query(User).one().senha_hash == self.original_hash,
                            'Expired attempt committed its hash upgrade')
        finally:
            db.close()

    def test_invalidated_successful_result_does_not_create_session(self):
        entered, release = threading.Event(), threading.Event()

        def work(_plain, _stored):
            entered.set()
            if not release.wait(10):
                raise AssertionError('Invalidated work release timed out')
            return True, None

        with patch.object(security.password_hash, 'verify_and_update', side_effect=work):
            with ThreadPoolExecutor(max_workers=1) as pool:
                pending = pool.submit(self.login)
                try:
                    self.assertTrue(entered.wait(10))
                    db = main.SessionLocal()
                    try:
                        db.query(LoginAttempt).update({LoginAttempt.em_andamento: False}, synchronize_session=False)
                        db.commit()
                    finally:
                        db.close()
                finally:
                    release.set()
                status, body, headers = pending.result(timeout=15)
        self.assertEqual(status, 503)
        self.assertNotIn('access_token', body)
        self.assertNotIn('set-cookie', headers)
        self.assert_no_session()

    def test_http_cancellation_keeps_hash_capacity_and_invalidates_result(self):
        entered, release = threading.Event(), threading.Event()

        def work(_plain, _stored):
            first = not entered.is_set()
            entered.set()
            if first and not release.wait(10):
                raise AssertionError('Cancelled work release timed out')
            return True, None

        payload = {'email': 'capacity@example.com', 'senha': 'fixture-capacity-password'}
        async def receive():
            return {'type': 'http.request', 'body': json.dumps(payload).encode(), 'more_body': False}
        request = Request({'type': 'http', 'method': 'POST', 'path': '/auth/login',
                           'headers': [], 'client': ('127.0.0.1', 1)}, receive)

        def route():
            db = main.SessionLocal()
            try:
                response = Response()
                try:
                    result = auth.login_user(UserLogin(**payload), request, response, db)
                    return 200, 'access_token' in result, bool(response.headers.get('set-cookie'))
                except HTTPException as error:
                    return error.status_code, False, False
            finally:
                db.close()

        async def scenario(pool):
            worker = None
            async def call_next(_request):
                nonlocal worker
                worker = pool.submit(route)
                await asyncio.wrap_future(worker)
                return JSONResponse({})
            task = asyncio.create_task(login_rate_limit.limit_login(request, call_next, Mock()))
            try:
                self.assertTrue(await asyncio.to_thread(entered.wait, 10))
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                with self.assertRaises(HTTPException) as blocked:
                    security.verify_password_and_update('fixture', 'fixture-hash')
                self.assertEqual(blocked.exception.status_code, 503)
            finally:
                release.set()
            return await asyncio.to_thread(worker.result, 15)

        with patch.object(security.password_hash, 'verify_and_update', side_effect=work):
            with ThreadPoolExecutor(max_workers=1) as pool:
                result = asyncio.run(scenario(pool))
        self.assertEqual(result, (503, False, False))
        self.assert_no_session()
        self.assertEqual(self.login()[0], 200)

    def test_missing_admission_cannot_issue_session(self):
        request = Request({'type': 'http', 'headers': [], 'client': ('127.0.0.1', 1)})
        db = main.SessionLocal()
        try:
            with self.assertRaises(HTTPException) as rejected:
                auth.login_user(UserLogin(email='capacity@example.com', senha='fixture-capacity-password'),
                                request, Response(), db)
            self.assertEqual(rejected.exception.status_code, 503)
        finally:
            db.close()
        self.assert_no_session()

    @unittest.skipUnless(os.environ.get('BOOKING_TEST_BACKEND') == 'postgresql',
                         'Requires explicitly configured disposable PostgreSQL')
    def test_postgresql_admission_coordinates_independent_processes(self):
        # Children inherit ONLY the harness's configured *_test database/schema.
        # Do not import support in children: that would create different schemas.
        script = '''
import sys
try:
    from app.core.login_rate_limit import reserve, Limited
    print("ready", flush=True)
    sys.stdin.readline()
    try:
        reserve("127.0.0.1", "process-capacity@example.com")
        print("admitted", flush=True)
    except Limited:
        print("limited", flush=True)
except Exception as error:
    print("error:" + type(error).__name__, flush=True)
    sys.exit(1)
'''
        children = []
        readers = ThreadPoolExecutor(max_workers=3)
        environment = dict(os.environ,
                           DATABASE_URL=main.engine.url.render_as_string(hide_password=False),
                           PYTHON_DOTENV_DISABLED='1', PYTHONDONTWRITEBYTECODE='1')
        try:
            for _ in range(3):
                child = subprocess.Popen([sys.executable, '-B', '-c', script],
                                         cwd=Path(__file__).resolve().parents[1], env=environment,
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, text=True)
                children.append(child)
            ready = [readers.submit(child.stdout.readline) for child in children]
            for result in ready:
                self.assertEqual(result.result(timeout=15).strip(), 'ready')
            for child in children:
                child.stdin.write('start\n')
                child.stdin.flush()
            results = []
            for child in children:
                stdout, _stderr = child.communicate(timeout=15)
                self.assertEqual(child.returncode, 0)
                results.append(stdout.strip())
            self.assertEqual(results.count('admitted'), 2)
            self.assertEqual(results.count('limited'), 1)
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                child.communicate(timeout=15)
            readers.shutdown(wait=True, cancel_futures=True)
