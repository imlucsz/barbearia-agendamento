"""Credential rejection is independent of transient service unavailability."""
import asyncio
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

from fastapi import Request

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core import login_rate_limit as limiter, security
from app.core.clock import utc_now_naive
from app.models.user import LoginAttempt, User, RefreshToken


class LoginOutcomeTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment('test').app
        self.now = utc_now_naive()
        for context in (
            patch.dict(os.environ, {'CLIENT_IP_SOURCE': 'direct'}),
            patch.object(limiter, 'utc_now_naive', side_effect=lambda: self.now),
            patch.object(security, '_password_verification_slots', threading.BoundedSemaphore(1)),
        ):
            context.start()
            self.addCleanup(context.stop)
        db = main.SessionLocal()
        try:
            db.add(User(nome='Conta Ficticia', email='outcome@example.com',
                        senha_hash=security.get_password_hash('fixture-outcome-password'),
                        consentimento_lgpd=True))
            db.commit()
        finally:
            db.close()

    def login(self, email='outcome@example.com', password='fixture-outcome-password'):
        return asgi_request(self.app, 'POST', '/auth/login', {'email': email, 'senha': password},
                            return_headers=True)

    def rows(self):
        db = main.SessionLocal()
        try:
            return db.query(LoginAttempt).order_by(LoginAttempt.id).all()
        finally:
            db.close()

    def busy_requests(self, count, distinct=False):
        slots = security._password_verification_slots
        self.assertTrue(slots.acquire(blocking=False))
        try:
            with patch.object(security.password_hash, 'verify_and_update') as verify:
                for number in range(count):
                    email = f'neutral-{number}@example.com' if distinct else 'outcome@example.com'
                    self.assertEqual(self.login(email)[0], 503)
                verify.assert_not_called()
        finally:
            slots.release()

    def test_five_busy_responses_do_not_consume_account_failures(self):
        self.busy_requests(5)
        self.assertEqual(self.login()[0], 200)
        rows = self.rows()
        self.assertTrue(all(row.resultado == 'neutro' and not row.sucesso for row in rows[:5]))
        self.assertEqual(rows[-1].resultado, 'sucesso')

    def test_thirty_busy_responses_do_not_consume_ip_failures(self):
        self.busy_requests(30, distinct=True)
        self.assertEqual(self.login()[0], 200)
        self.assertEqual(sum(row.resultado == 'credencial_rejeitada' for row in self.rows()), 0)

    def test_busy_responses_still_consume_request_budget(self):
        self.busy_requests(60, distinct=True)
        status, _, headers = self.login()
        self.assertEqual(status, 429)
        self.assertEqual(headers['retry-after'], '60')
        self.assertEqual(len(self.rows()), 60)
        self.assertTrue(all(row.resultado == 'neutro' for row in self.rows()))

    def test_real_wrong_passwords_still_reach_account_limit(self):
        for _ in range(5):
            self.assertEqual(self.login(password='invalid-fixture-password')[0], 401)
        self.assertEqual(self.login()[0], 429)
        self.assertTrue(all(row.resultado == 'credencial_rejeitada' for row in self.rows()))

    def test_finish_is_conditional_and_does_not_overwrite_terminal_result(self):
        identifier = limiter.reserve('127.0.0.1', 'outcome@example.com')
        self.assertTrue(limiter.finish(identifier, limiter.Outcome.NEUTRAL, limiter.Reason.UNAVAILABLE))
        self.assertFalse(limiter.finish(identifier, limiter.Outcome.REJECTED, limiter.Reason.REJECTED))
        row = self.rows()[0]
        self.assertEqual((row.resultado, row.motivo_finalizacao, row.sucesso),
                         ('neutro', 'indisponivel', False))

    def test_concurrent_finalizers_have_one_winner(self):
        identifier = limiter.reserve('127.0.0.1', 'outcome@example.com')
        with ThreadPoolExecutor(max_workers=2) as pool:
            calls = [pool.submit(limiter.finish, identifier, limiter.Outcome.NEUTRAL, reason)
                     for reason in (limiter.Reason.CANCELLED, limiter.Reason.UNAVAILABLE)]
            self.assertEqual(sum(call.result(timeout=10) for call in calls), 1)
        self.assertEqual(len(self.rows()), 1)

    def test_expired_pending_reservation_is_not_a_password_failure(self):
        policy = replace(limiter.POLICY, account_failures=1, ip_failures=1,
                         account_concurrency=10, ip_concurrency=10)
        with patch.object(limiter, 'POLICY', policy):
            first = limiter.reserve('127.0.0.1', 'outcome@example.com')
            with self.assertRaises(limiter.Limited):
                limiter.reserve('127.0.0.1', 'outcome@example.com')
            self.now += timedelta(seconds=limiter.POLICY.lease_seconds + 1)
            second = limiter.reserve('127.0.0.1', 'outcome@example.com')
            self.assertTrue(limiter.finish(first, limiter.Outcome.NEUTRAL, limiter.Reason.EXPIRED))
            self.assertTrue(limiter.finish(second, limiter.Outcome.NEUTRAL, limiter.Reason.UNAVAILABLE))
        self.assertTrue(all(row.resultado == 'neutro' for row in self.rows()))
        self.assertEqual(self.rows()[0].motivo_finalizacao, 'expirada')

    def test_cancelled_reservation_is_neutral(self):
        async def receive():
            return {'type': 'http.request', 'body': b'{"email":"outcome@example.com","senha":"fixture"}',
                    'more_body': False}
        request = Request({'type': 'http', 'headers': [], 'client': ('127.0.0.1', 1)}, receive)
        async def cancel(_request):
            raise asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(limiter.limit_login(request, cancel, lambda: None))
        row = self.rows()[0]
        self.assertEqual((row.resultado, row.motivo_finalizacao, row.sucesso),
                         ('neutro', 'cancelada', False))
        self.assertEqual(self.login()[0], 200)

    def test_error_after_rejected_credential_keeps_real_verdict(self):
        with patch('app.routers.auth.record_audit', side_effect=RuntimeError('fixture-audit-error')):
            self.assertEqual(self.login(password='invalid-fixture-password')[0], 503)
        row = self.rows()[0]
        self.assertEqual((row.resultado, row.motivo_finalizacao),
                         ('credencial_rejeitada', 'erro_apos_rejeicao'))
        self.assertFalse(limiter.finish(row.id, limiter.Outcome.NEUTRAL, limiter.Reason.UNAVAILABLE))

    def test_cancel_after_known_rejection_keeps_real_verdict(self):
        async def receive():
            return {'type': 'http.request', 'body': b'{"email":"outcome@example.com","senha":"fixture"}',
                    'more_body': False}
        request = Request({'type': 'http', 'headers': [], 'client': ('127.0.0.1', 1)}, receive)
        async def reject_then_cancel(request):
            limiter.record_login_outcome(request, limiter.Outcome.REJECTED, limiter.Reason.REJECTED)
            raise asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(limiter.limit_login(request, reject_then_cancel, lambda: None))
        row = self.rows()[0]
        self.assertEqual((row.resultado, row.motivo_finalizacao),
                         ('credencial_rejeitada', 'interrompida_apos_rejeicao'))

    def test_expiry_does_not_erase_a_known_credential_rejection(self):
        identifier = limiter.reserve('127.0.0.1', 'outcome@example.com')
        self.now += timedelta(seconds=limiter.POLICY.lease_seconds + 1)
        self.assertTrue(limiter.finish(identifier, limiter.Outcome.REJECTED, limiter.Reason.REJECTED))
        self.assertEqual(self.rows()[0].resultado, 'credencial_rejeitada')

    def test_legacy_expired_reservation_preserves_original_binary_budget(self):
        db = main.SessionLocal()
        try:
            db.add(LoginAttempt(ip='127.0.0.1', rota='/auth/login', sucesso=False,
                                ocorrido_em=self.now - timedelta(seconds=121), em_andamento=True,
                                expira_em=self.now - timedelta(seconds=1)))
            db.commit()
        finally:
            db.close()
        with patch.object(limiter, 'POLICY', replace(limiter.POLICY, ip_failures=1)):
            with self.assertRaises(limiter.Limited):
                limiter.reserve('127.0.0.1', 'outcome@example.com')

    def test_error_after_valid_credential_is_neutral_and_rolls_back_session(self):
        with patch('app.routers.auth.record_audit', side_effect=RuntimeError('fixture-audit-error')):
            status, body, headers = self.login()
        self.assertEqual(status, 503)
        self.assertNotIn('access_token', body)
        self.assertNotIn('set-cookie', headers)
        self.assertEqual(self.rows()[0].resultado, 'neutro')
        db = main.SessionLocal()
        try:
            self.assertEqual(db.query(RefreshToken).count(), 0)
        finally:
            db.close()

    def test_legacy_binary_history_keeps_conservative_window_semantics(self):
        db = main.SessionLocal()
        try:
            db.add_all([LoginAttempt(ip='127.0.0.1', rota='/auth/login', sucesso=value,
                                     ocorrido_em=self.now) for value in (False, True, False)])
            db.commit()
        finally:
            db.close()
        with patch.object(limiter, 'POLICY', replace(limiter.POLICY, ip_failures=2)):
            with self.assertRaises(limiter.Limited):
                limiter.reserve('127.0.0.1', 'outcome@example.com')
            self.now += timedelta(seconds=limiter.POLICY.ip_window_seconds)
            self.assertIsInstance(limiter.reserve('127.0.0.1', 'outcome@example.com'), int)
