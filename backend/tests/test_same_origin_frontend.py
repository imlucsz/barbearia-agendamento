"""Origin-unified frontend publication and session regression contracts."""
# ruff: noqa: I001
import os
import unittest
from unittest.mock import patch
from support import asgi_request, load_app_for_environment, main, reset_database
from app.models.user import RefreshToken


class SameOriginFrontendTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.env = patch.dict(os.environ, {'SERVE_FRONTEND': 'true'})
        self.env.start()
        def cleanup():
            self.env.stop()
            load_app_for_environment('test')
        self.addCleanup(cleanup)
        self.app = load_app_for_environment('test').app

    def test_public_pages_receive_same_origin_configuration_and_usable_csp(self):
        status, html, headers = asgi_request(self.app, 'GET', '/pages/login.html', return_headers=True)
        self.assertEqual(status, 200)
        self.assertIn('/assets/js/same-origin-config.js', html)
        self.assertLess(html.index('same-origin-config.js'), html.index('type="module"'))
        self.assertNotIn("default-src 'none'", headers['content-security-policy'])
        self.assertIn("frame-ancestors 'none'", headers['content-security-policy'])
        self.assertEqual(headers['cache-control'], 'no-store')
        status, _, script_headers = asgi_request(self.app, 'GET', '/assets/js/same-origin-config.js', return_headers=True)
        self.assertEqual(status, 200)
        self.assertIn('javascript', script_headers['content-type'])

    def test_api_headers_and_private_files_remain_protected(self):
        _, _, headers = asgi_request(self.app, 'GET', '/auth/me', return_headers=True)
        self.assertIn("default-src 'none'", headers['content-security-policy'])
        self.assertEqual(headers['cache-control'], 'no-store')
        for path in ('/.env', '/backend/requirements.txt', '/scripts/build-static.mjs',
                     '/pages/../requirements.txt', '/assets/../../backend/.env'):
            self.assertEqual(asgi_request(self.app, 'GET', path)[0], 404, path)

    def test_root_redirect_only_in_explicit_web_mode(self):
        status, _, headers = asgi_request(self.app, 'GET', '/', return_headers=True)
        self.assertEqual(status, 307)
        self.assertEqual(headers['location'], '/pages/index.html')
        with patch.dict(os.environ, {'SERVE_FRONTEND': 'false'}):
            api_only = load_app_for_environment('test').app
            self.assertEqual(asgi_request(api_only, 'GET', '/')[0], 200)
            self.assertEqual(asgi_request(api_only, 'GET', '/pages/login.html')[0], 404)

    def test_foreign_login_origin_is_rejected_without_creating_session(self):
        status, _ = asgi_request(self.app, 'POST', '/auth/login',
            {'email': 'fixture@example.com', 'senha': 'fictional-password'},
            headers={'Origin': 'https://untrusted.example'})
        self.assertEqual(status, 403)
        with main.SessionLocal() as db:
            self.assertEqual(db.query(RefreshToken).count(), 0)

    def test_session_mutations_reject_missing_null_and_unlisted_origins(self):
        for endpoint in ('refresh', 'logout'):
            for headers in ({}, {'Origin': 'null'}, {'Origin': 'https://untrusted.example'},
                            {'Origin': 'https://testserver'}):
                self.assertEqual(asgi_request(self.app, 'POST', '/auth/' + endpoint, headers=headers)[0], 403)
        status, _, headers = asgi_request(self.app, 'POST', '/auth/logout',
            headers={'Origin': 'https://frontend.test.invalid'}, return_headers=True)
        self.assertEqual(status, 200)
        self.assertEqual(headers['access-control-allow-origin'], 'https://frontend.test.invalid')
        self.assertEqual(headers['access-control-allow-credentials'], 'true')

    def test_cors_preflight_only_grants_the_explicit_origin(self):
        for origin, expected in (('https://frontend.test.invalid', 200), ('https://foreign.example', 400)):
            status, _, headers = asgi_request(self.app, 'OPTIONS', '/auth/login', headers={
                'Origin': origin, 'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'content-type'}, return_headers=True)
            self.assertEqual(status, expected)
            if expected == 400:
                self.assertNotIn('access-control-allow-origin', headers)

    def test_cache_head_methods_and_missing_paths(self):
        for path in ('/pages/login.html', '/assets/js/api.js'):
            status, _, headers = asgi_request(self.app, 'GET', path,
                headers={'If-None-Match': '*', 'If-Modified-Since': 'Wed, 01 Jan 2099 00:00:00 GMT'}, return_headers=True)
            self.assertEqual(status, 200)
            self.assertEqual(headers['cache-control'], 'no-store')
        status, body, headers = asgi_request(self.app, 'HEAD', '/pages/login.html', return_headers=True)
        self.assertEqual(status, 200)
        self.assertIsNone(body)
        self.assertGreater(int(headers['content-length']), 0)
        self.assertEqual(asgi_request(self.app, 'POST', '/pages/login.html')[0], 405)
        self.assertEqual(asgi_request(self.app, 'GET', '/pages/missing.html')[0], 404)
        self.assertEqual(asgi_request(self.app, 'GET', '/auth/me')[0], 401)
