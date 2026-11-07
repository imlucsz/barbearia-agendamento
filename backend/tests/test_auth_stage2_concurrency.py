"""Focused regressions for reservation lifetime and authentication lock order."""
import hashlib
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import text

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core import login_rate_limit, security
from app.core.clock import utc_now_naive
from app.core.security import get_password_hash, verify_password
from app.models.user import PasswordResetToken, User
from app.routers import auth


class Stage2ConcurrencyTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment('test').app
        environment = patch.dict(os.environ, {'CLIENT_IP_SOURCE': 'direct'})
        environment.start()
        self.addCleanup(environment.stop)
        self.password = 'fixture-lock-order-password'
        self.raw_reset = 'fixture-lock-order-reset'
        self.reset_digest = hashlib.sha256(self.raw_reset.encode()).hexdigest()
        db = main.SessionLocal()
        try:
            user = User(nome='Conta Ficticia', email='concurrency@example.com',
                        senha_hash=get_password_hash(self.password), consentimento_lgpd=True)
            db.add(user)
            db.flush()
            self.user_id = user.id
            db.add(PasswordResetToken(user_id=user.id, token=self.reset_digest,
                                      expires_at=utc_now_naive() + timedelta(hours=1), used=False))
            db.commit()
        finally:
            db.close()

    def login(self, password=None):
        return asgi_request(self.app, 'POST', '/auth/login', {
            'email': 'concurrency@example.com', 'senha': password or self.password,
        })

    def reset(self, token=None):
        return asgi_request(self.app, 'POST', '/auth/redefinir-senha', {
            'token': token or self.raw_reset, 'nova_senha': 'fixture-new-lock-order-password',
        })

    def test_active_password_work_must_not_lose_capacity_when_lease_expires(self):
        # Fill a configured capacity of two, then expire the distributed lease.
        # Native work still holds local capacity independently of that lease.
        now = datetime(2026, 11, 6, 12)
        two_active = threading.Event()
        release = threading.Event()
        mutex = threading.Lock()
        active = peak = entered = 0

        def gate(_password, _stored):
            nonlocal active, peak, entered
            with mutex:
                entered += 1
                ordinal = entered
                active += 1
                peak = max(peak, active)
                if active == 2:
                    two_active.set()
            try:
                if ordinal <= 2 and not release.wait(15):
                    raise AssertionError('Controlled password work release timed out')
                return False, None
            finally:
                with mutex:
                    active -= 1

        with patch.object(login_rate_limit, 'utc_now_naive', side_effect=lambda: now), \
                patch.object(security, '_password_verification_slots', threading.BoundedSemaphore(2)), \
                patch.object(security.password_hash, 'verify_and_update', side_effect=gate):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = [pool.submit(self.login, 'invalid-fixture') for _ in range(2)]
                try:
                    self.assertTrue(two_active.wait(10))
                    now += timedelta(seconds=login_rate_limit.POLICY.lease_seconds + 1)
                    later = [self.login('invalid-fixture')[0] for _ in range(2)]
                finally:
                    release.set()
                self.assertEqual([future.result(timeout=20)[0] for future in first], [401, 401])
        self.assertEqual(later, [503, 503], 'Active hash work lost its local capacity')
        self.assertLessEqual(peak, 2)

    def test_reset_locks_user_before_consuming_recovery_token(self):
        observed = []
        original = auth._lock_refresh_user

        def observe(db, user_id):
            # Query a scalar: the ORM instance can retain used=False after a bulk update.
            observed.append(db.query(PasswordResetToken.used).filter(
                PasswordResetToken.token == self.reset_digest).scalar())
            return original(db, user_id)

        with patch.object(auth, '_lock_refresh_user', side_effect=observe):
            self.assertEqual(self.reset()[0], 200)
        self.assertTrue(observed)
        self.assertIs(observed[0], False, 'Recovery token was locked before its User')
        self.assertEqual(self.reset()[0], 400)
        self.assertEqual(self.login()[0], 401)
        self.assertEqual(self.login('fixture-new-lock-order-password')[0], 200)

    def test_invalid_reset_does_not_acquire_user_lock(self):
        with patch.object(auth, '_lock_refresh_user') as lock:
            self.assertEqual(self.reset('invalid-fixture-token')[0], 400)
        lock.assert_not_called()

    def test_reset_rechecks_expiry_after_waiting_for_user(self):
        now = utc_now_naive()
        db = main.SessionLocal()
        try:
            db.query(PasswordResetToken).filter(PasswordResetToken.token == self.reset_digest).update(
                {PasswordResetToken.expires_at: now + timedelta(seconds=1)}, synchronize_session=False)
            db.commit()
        finally:
            db.close()
        original = auth._lock_refresh_user

        def wait_for_user(db, user_id):
            nonlocal now
            now += timedelta(seconds=2)
            return original(db, user_id)

        with patch.object(auth, 'utc_now_naive', side_effect=lambda: now), \
                patch.object(auth, '_lock_refresh_user', side_effect=wait_for_user):
            self.assertEqual(self.reset()[0], 400)
        db = main.SessionLocal()
        try:
            self.assertFalse(db.query(PasswordResetToken.used).filter(
                PasswordResetToken.token == self.reset_digest).scalar())
            self.assertTrue(verify_password(self.password, db.get(User, self.user_id).senha_hash))
        finally:
            db.close()

    @unittest.skipUnless(os.environ.get('BOOKING_TEST_BACKEND') == 'postgresql',
                         'Requires explicitly configured disposable PostgreSQL')
    def test_postgresql_erasure_can_finish_before_waiting_reset_without_deadlock(self):
        # Same interleaving creates a User <-> PasswordResetToken lock cycle in old code.
        status, body = self.login()
        self.assertEqual(status, 200)
        authorization = {'Authorization': 'Bearer ' + body['access_token']}
        reset_at_user_lock = threading.Event()
        erasure_has_user = threading.Event()
        operation = ContextVar('stage2_lock_order_operation', default=None)
        original = auth._lock_refresh_user

        def gate(db, user_id):
            db.execute(text("SET LOCAL lock_timeout = '5s'"))
            if operation.get() == 'reset' and not reset_at_user_lock.is_set():
                reset_at_user_lock.set()
                if not erasure_has_user.wait(10):
                    raise AssertionError('Erasure did not acquire User')
            original(db, user_id)
            if operation.get() == 'erasure':
                erasure_has_user.set()

        def worker(kind):
            operation.set(kind)
            try:
                if kind == 'reset':
                    return self.reset()[0]
                return asgi_request(self.app, 'DELETE', '/users/me',
                                    {'senha_atual': self.password}, headers=authorization)[0]
            except Exception as error:
                # Assertion output must not include SQL parameters, hashes or tokens.
                return ('error', type(error).__name__)

        with patch.object(auth, '_lock_refresh_user', side_effect=gate):
            with ThreadPoolExecutor(max_workers=2) as pool:
                reset = pool.submit(worker, 'reset')
                self.assertTrue(reset_at_user_lock.wait(10))
                erasure = pool.submit(worker, 'erasure')
                self.assertEqual(erasure.result(timeout=20), 200)
                self.assertEqual(reset.result(timeout=20), 400)
        db = main.SessionLocal()
        try:
            self.assertFalse(db.get(User, self.user_id).ativo)
            self.assertEqual(db.query(PasswordResetToken).filter(
                PasswordResetToken.user_id == self.user_id).count(), 0)
        finally:
            db.close()
