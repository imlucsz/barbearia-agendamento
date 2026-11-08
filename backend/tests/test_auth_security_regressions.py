import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch
import bcrypt
from support import asgi_request, load_app_for_environment, main, reset_database
from app.models.user import User, RoleEnum, RefreshToken
from app.core.security import verify_password
from app.routers import auth

class AuthenticationSecurityTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        os.environ['CLIENT_IP_SOURCE'] = 'direct'
        self.app = load_app_for_environment('test').app

    def request(self, method, path, payload=None, token=None):
        headers = {'Authorization': 'Bearer ' + token} if token else None
        return asgi_request(self.app, method, path, payload, headers=headers)

    def test_legacy_login_cannot_overwrite_completed_reset(self):
        self.assert_reset_wins(legacy=True)

    def test_argon_login_cannot_issue_session_after_completed_reset(self):
        self.assert_reset_wins(legacy=False)

    def assert_reset_wins(self, *, legacy):
        old_password = 'fixture-legacy-only-2026'
        new_password = 'fixture-replacement-only-2026'
        db = main.SessionLocal()
        try:
            user = User(nome='Conta Legada', email='legacy-validation@example.com',
                        senha_hash=(bcrypt.hashpw(old_password.encode(), bcrypt.gensalt(rounds=12)).decode()
                                    if legacy else auth.get_password_hash(old_password)),
                        role=RoleEnum.CLIENTE, consentimento_lgpd=True)
            db.add(user)
            db.commit()
            identifier = user.id
        finally:
            db.close()
        with patch('app.routers.auth.send_password_reset_email') as delivery:
            status, _ = self.request('POST', '/auth/esqueci-senha',
                                     {'email': 'legacy-validation@example.com'})
        self.assertEqual(status, 200)
        reset_token = delivery.call_args.args[1]
        verified = Event()
        resume = Event()
        original_verify = auth.verify_password_and_update
        def gated_verify(password, stored):
            result = original_verify(password, stored)
            if not result[0] or (legacy and result[1] is None):
                raise AssertionError('Credential verification precondition missing')
            verified.set()
            if not resume.wait(30):
                raise AssertionError('Controlled login resume timed out')
            return result
        with ThreadPoolExecutor(max_workers=1) as pool:
            with patch('app.routers.auth.verify_password_and_update', side_effect=gated_verify):
                future = pool.submit(asgi_request, self.app, 'POST', '/auth/login',
                                     {'email': 'legacy-validation@example.com', 'senha': old_password},
                                     return_headers=True)
                try:
                    self.assertTrue(verified.wait(30), 'Login did not reach the synchronization point')
                    reset_status, _ = self.request('POST', '/auth/redefinir-senha',
                                                   {'token': reset_token, 'nova_senha': new_password})
                    self.assertEqual(reset_status, 200)
                    db = main.SessionLocal()
                    try:
                        before = db.query(User).filter_by(id=identifier).one().senha_hash
                    finally:
                        db.close()
                    self.assertTrue(verify_password(new_password, before), 'Reset did not commit new credential')
                    self.assertFalse(verify_password(old_password, before), 'Reset retained old credential')
                finally:
                    resume.set()
                login_status, login_body, login_headers = future.result(timeout=30)
        db = main.SessionLocal()
        try:
            after = db.query(User).filter_by(id=identifier).one().senha_hash
            self.assertEqual(db.query(RefreshToken).filter_by(user_id=identifier).count(), 0)
        finally:
            db.close()
        old_accepted = verify_password(old_password, after)
        new_accepted = verify_password(new_password, after)
        self.assertFalse(old_accepted, 'Delayed login restored the previous credential')
        self.assertTrue(new_accepted, 'Delayed login invalidated the replacement credential')
        self.assertEqual(login_status, 401, 'Stale credential issued a new session after reset')
        self.assertFalse('access_token' in login_body)
        self.assertFalse('set-cookie' in login_headers)
        self.assertEqual(self.request('POST', '/auth/login', {
            'email': 'legacy-validation@example.com', 'senha': old_password})[0], 401)
        self.assertEqual(self.request('POST', '/auth/login', {
            'email': 'legacy-validation@example.com', 'senha': new_password})[0], 200)

    def test_access_token_cannot_follow_reused_email_to_new_account(self):
        email = 'identity-validation@example.com'
        password_a = 'fixture-owner-a-only-2026'
        password_b = 'fixture-owner-b-only-2026'
        status, account_a = self.request('POST', '/auth/register', {
            'nome': 'Conta Original', 'email': email, 'senha': password_a, 'consentimento_lgpd': True})
        self.assertEqual(status, 201)
        status, session_a = self.request('POST', '/auth/login', {'email': email, 'senha': password_a})
        self.assertEqual(status, 200)
        token_a = session_a['access_token']
        status, me = self.request('GET', '/auth/me', token=token_a)
        self.assertEqual(status, 200)
        self.assertEqual(me['id'], account_a['id'])
        status, _ = self.request('DELETE', '/users/me', {'senha_atual': password_a}, token=token_a)
        self.assertEqual(status, 200)
        status_before_reuse, _ = self.request('GET', '/auth/me', token=token_a)
        self.assertEqual(status_before_reuse, 401)
        status, account_b = self.request('POST', '/auth/register', {
            'nome': 'Conta Nova', 'email': email, 'senha': password_b, 'consentimento_lgpd': True})
        self.assertEqual(status, 201)
        self.assertNotEqual(account_a['id'], account_b['id'])
        status, session_b = self.request('POST', '/auth/login', {'email': email, 'senha': password_b})
        self.assertEqual(status, 200)
        status, me_b = self.request('GET', '/auth/me', token=session_b['access_token'])
        self.assertEqual(status, 200)
        self.assertEqual(me_b['id'], account_b['id'])
        reused_status, resolved = self.request('GET', '/auth/me', token=token_a)
        self.assertEqual(reused_status, 401, 'Original token authenticated the replacement account')

    def test_email_change_does_not_transfer_token_identity(self):
        status, account_a = self.request('POST', '/auth/register', {
            'nome': 'Conta Original', 'email': 'reuse-change@example.com',
            'senha': 'fixture-a-password', 'consentimento_lgpd': True})
        self.assertEqual(status, 201)
        status, session_a = self.request('POST', '/auth/login', {
            'email': 'reuse-change@example.com', 'senha': 'fixture-a-password'})
        self.assertEqual(status, 200)
        db = main.SessionLocal()
        try:
            db.query(User).filter_by(id=account_a['id']).update({'email': 'changed@example.com'})
            db.commit()
        finally:
            db.close()
        status, account_b = self.request('POST', '/auth/register', {
            'nome': 'Conta Nova', 'email': 'reuse-change@example.com',
            'senha': 'fixture-b-password', 'consentimento_lgpd': True})
        self.assertEqual(status, 201)
        status, resolved = self.request('GET', '/auth/me', token=session_a['access_token'])
        self.assertEqual(status, 200)
        self.assertEqual(resolved['id'], account_a['id'])
        self.assertNotEqual(resolved['id'], account_b['id'])

    def test_legacy_malformed_expired_and_invalid_tokens_are_rejected(self):
        import jwt
        from datetime import timedelta
        from support import TEST_SECRET_KEY
        from app.core.clock import utc_now
        from app.core.security import ALGORITHM, create_access_token
        status, account = self.request('POST', '/auth/register', {
            'nome': 'Conta Teste', 'email': 'signed-token@example.com',
            'senha': 'fixture-password-only', 'consentimento_lgpd': True})
        self.assertEqual(status, 201)
        subject_id = str(account['id'])
        self.assertEqual(self.request('GET', '/auth/me', token=create_access_token({'sub': subject_id}))[0], 200)
        expiry = utc_now() + timedelta(minutes=5)
        for subject in ('old@example.com', '', '0', '-1', '01', '2147483648', '１', 1, None):
            with self.subTest(subject_type=type(subject).__name__):
                token = jwt.encode({'sub': subject, 'exp': expiry}, TEST_SECRET_KEY, algorithm=ALGORITHM)
                self.assertEqual(self.request('GET', '/auth/me', token=token)[0], 401)
                with self.assertRaises(ValueError):
                    create_access_token({'sub': subject})
        for payload, key in (
            ({'sub': subject_id, 'exp': utc_now() - timedelta(seconds=1)}, TEST_SECRET_KEY),
            ({'sub': subject_id}, TEST_SECRET_KEY),
            ({'exp': expiry}, TEST_SECRET_KEY),
            ({'sub': subject_id, 'exp': expiry}, 'fixture-wrong-key-only-not-for-deployment'),
        ):
            token = jwt.encode(payload, key, algorithm=ALGORITHM)
            self.assertEqual(self.request('GET', '/auth/me', token=token)[0], 401)
        self.assertEqual(self.request('GET', '/auth/me', token='invalid-token')[0], 401)

    def test_inactive_blocked_and_unknown_user_ids_remain_rejected(self):
        from app.core.security import create_access_token
        status, account = self.request('POST', '/auth/register', {
            'nome': 'Conta Teste', 'email': 'state@example.com',
            'senha': 'fixture-password-only', 'consentimento_lgpd': True})
        self.assertEqual(status, 201)
        token = create_access_token({'sub': str(account['id'])})
        self.assertEqual(self.request('GET', '/auth/me', token=token)[0], 200)
        db = main.SessionLocal()
        try:
            db.query(User).filter_by(id=account['id']).update({'ativo': False})
            db.commit()
            self.assertEqual(self.request('GET', '/auth/me', token=token)[0], 401)
            db.query(User).filter_by(id=account['id']).update({'ativo': True, 'bloqueado': True})
            db.commit()
            self.assertEqual(self.request('GET', '/auth/me', token=token)[0], 403)
        finally:
            db.close()
        self.assertEqual(self.request('GET', '/auth/me', token=create_access_token({'sub': '2147483647'}))[0], 401)

    def test_refresh_issues_access_token_for_same_immutable_id(self):
        from http.cookies import SimpleCookie
        from app.core.security import decode_access_token
        status, account = self.request('POST', '/auth/register', {
            'nome': 'Conta Teste', 'email': 'refresh-id@example.com',
            'senha': 'fixture-password-only', 'consentimento_lgpd': True})
        self.assertEqual(status, 201)
        status, login, headers = asgi_request(self.app, 'POST', '/auth/login', {
            'email': 'refresh-id@example.com', 'senha': 'fixture-password-only'}, return_headers=True)
        self.assertEqual(status, 200)
        cookie = SimpleCookie()
        cookie.load(headers['set-cookie'])
        status, refreshed = asgi_request(self.app, 'POST', '/auth/refresh', headers={
            'Cookie': 'refresh_token=' + cookie['refresh_token'].value,
            'Origin': 'https://frontend.test.invalid',
        })
        self.assertEqual(status, 200)
        self.assertEqual(decode_access_token(login['access_token'])['sub'], str(account['id']))
        self.assertEqual(decode_access_token(refreshed['access_token'])['sub'], str(account['id']))
        self.assertEqual(self.request('GET', '/auth/me', token=refreshed['access_token'])[0], 200)


if __name__ == '__main__':
    unittest.main()
