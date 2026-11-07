"""HTTPS-only local F1 fixture: isolated SQLite, fictional account, no published data."""
# ruff: noqa: I001
# Test support must initialize isolation before any application modules are loaded.
import argparse
import importlib
import os
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'backend/tests')]
os.environ['BOOKING_TEST_BACKEND'] = 'sqlite'
os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=4197)
    parser.add_argument('--certfile', required=True)
    parser.add_argument('--keyfile', required=True)
    parser.add_argument('--evil-port', type=int, default=4198)
    args = parser.parse_args()
    from support import main as application, reset_database
    from app.core.clock import utc_now_naive
    from app.core.security import get_password_hash
    from app.models.user import User, RefreshToken
    from app.core import login_rate_limit
    import jwt
    import uvicorn
    reset_database()
    fixture_settings = login_rate_limit.settings()
    # Keep the HMAC store on the explicit test settings while exercising production cookie flags.
    # Production settings correctly refuse this SQLite fixture and its public test secret.
    login_rate_limit.settings = lambda: fixture_settings
    origin = f'https://127.0.0.1:{args.port}'
    os.environ.update(APP_ENV='production', SERVE_FRONTEND='true', FORCE_HTTPS='true',
                      CORS_ALLOWED_ORIGINS=origin + f',https://localhost:{args.port}',
                      ALLOWED_HOSTS='127.0.0.1,localhost', CLIENT_IP_SOURCE='direct')
    # Only the app module is reloaded: database/settings remain the test harness's isolated objects.
    application = importlib.reload(application)
    with application.SessionLocal() as db:
        user = User(nome='Conta F1 Ficticia', email='browser-f1@example.com',
                    senha_hash=get_password_hash('fixture-browser-password'), consentimento_lgpd=True)
        db.add(user)
        db.commit()
        identifier = user.id

    @application.app.get('/__qa__/expired-access')
    def expired_access():
        from support import TEST_SECRET_KEY
        return {'access_token': jwt.encode({'sub': str(identifier), 'exp': utc_now_naive() - timedelta(seconds=1)}, TEST_SECRET_KEY, algorithm='HS256')}

    @application.app.get('/__qa__/state')
    def state():
        with application.SessionLocal() as db:
            rows = db.query(RefreshToken).all()
            return {'refresh_rows': len(rows), 'active': sum(r.revoked_at is None for r in rows),
                    'revoked': sum(r.revoked_at is not None for r in rows),
                    'families': len({r.family_id for r in rows})}

    @application.app.get('/__qa__/runtime')
    def runtime():
        from importlib.metadata import version
        return {'python': sys.version.split()[0], 'pydantic': version('pydantic'),
                'python-multipart': version('python-multipart'), 'fastapi': version('fastapi')}

    @application.app.post('/__qa__/revoke-fixture-sessions')
    def revoke_fixture_sessions():
        with application.SessionLocal() as db:
            db.query(RefreshToken).filter(RefreshToken.user_id == identifier).update(
                {RefreshToken.revoked_at: utc_now_naive()}, synchronize_session=False)
            db.commit()
        return {'ok': True}

    @application.app.get('/__qa__/browser-test.js')
    def browser_test():
        from starlette.responses import FileResponse
        return FileResponse(ROOT / 'frontend/e2e/auth-session-browser.mjs', media_type='text/javascript')

    # A sibling origin (same site, different port) can send Lax cookies; Origin must reject it.
    import ssl
    import threading
    import atexit
    import mimetypes
    import subprocess
    import tempfile
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import unquote, urlsplit

    legacy_tmp = tempfile.TemporaryDirectory(prefix='barbearia-f1-legacy-')
    atexit.register(legacy_tmp.cleanup)
    subprocess.run(['node', str(ROOT / 'frontend/e2e/build-legacy-fixture.mjs'), legacy_tmp.name, origin],
                   check=True, timeout=30)
    legacy_dist = (Path(legacy_tmp.name) / 'frontend/dist').resolve()

    class ForeignPage(BaseHTTPRequestHandler):
        def do_GET(self):
            target = (legacy_dist / unquote(urlsplit(self.path).path).lstrip('/')).resolve()
            if target.is_relative_to(legacy_dist) and target.is_file():
                self.send_response(200)
                self.send_header('Content-Type', mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
                self.end_headers()
                self.wfile.write(target.read_bytes())
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<!doctype html><title>Foreign origin fixture</title>')

        def log_message(self, *_args):
            pass

    foreign = ThreadingHTTPServer(('127.0.0.1', args.evil_port), ForeignPage)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(args.certfile, args.keyfile)
    foreign.socket = tls.wrap_socket(foreign.socket, server_side=True)
    threading.Thread(target=foreign.serve_forever, daemon=True).start()

    uvicorn.run(application.app, host='127.0.0.1', port=args.port, ssl_certfile=args.certfile,
                ssl_keyfile=args.keyfile, access_log=False, log_level='error')


if __name__ == '__main__':
    main()
