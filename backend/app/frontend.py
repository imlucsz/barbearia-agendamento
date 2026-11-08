"""Optional public frontend on the API origin; never expose the repository root."""
import asyncio
import os
from pathlib import Path

from starlette.responses import FileResponse, HTMLResponse
from starlette.staticfiles import StaticFiles

FRONTEND_CSP = "frame-ancestors 'none'; base-uri 'self'; object-src 'none'"


class FreshStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        # Stable asset URLs must not mix modules from different releases.
        scope = dict(scope)
        scope['headers'] = [(k, v) for k, v in scope.get('headers', [])
                            if k.lower() not in (b'if-none-match', b'if-modified-since')]
        response = await super().get_response(path, scope)
        response.headers['Cache-Control'] = 'no-store'
        return response


class FrontendPages(FreshStaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse) and str(response.path).endswith('.html'):
            # StaticFiles already enforces containment and denies directory traversal.
            html = await asyncio.to_thread(Path(response.path).read_text, encoding='utf-8')
            injection = '<script src="/assets/js/same-origin-config.js"></script>\n'
            html = html.replace('</head>', injection + '</head>', 1)
            scope.setdefault('state', {})['frontend_document'] = True
            response = HTMLResponse('' if scope['method'] == 'HEAD' else html,
                                    status_code=response.status_code,
                                    headers={'Cache-Control': 'no-store',
                                             'Content-Length': str(len(html.encode('utf-8')))})
        return response


def install_frontend(app):
    value = os.environ.get('SERVE_FRONTEND', 'false').strip().lower()
    if value not in {'true', 'false'}:
        raise RuntimeError('SERVE_FRONTEND must be true or false')
    if value == 'false':
        return False
    root = Path(__file__).resolve().parents[2] / 'frontend'
    # Only these public directories are mounted. No build tooling, backend or env files.
    app.mount('/pages', FrontendPages(directory=root / 'pages'), name='frontend-pages')
    app.mount('/assets', FreshStaticFiles(directory=root / 'assets'), name='frontend-assets')
    return True
