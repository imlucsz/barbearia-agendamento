import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException, Request

from app.core.request_context import get_client_ip
from support import main


def request_with_ip(remote_ip="127.0.0.1", forwarded_for=None):
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode("ascii")))
    return Request({
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "GET", "scheme": "http", "path": "/", "raw_path": b"/",
        "query_string": b"", "headers": headers,
        "client": (remote_ip, 1234), "server": ("testserver", 80),
    })


class RequestContextTests(unittest.TestCase):
    def get_ip(self, proxy_count, request):
        environment = {
            "APP_ENV": "test",
            "DATABASE_URL": str(main.engine.url),
            "SECRET_KEY": "request-context-test-key-not-a-real-secret-2026",
            "TRUSTED_PROXY_COUNT": str(proxy_count),
            "CORS_ALLOWED_ORIGINS": "https://frontend.test.invalid",
        }
        with patch.dict(os.environ, environment, clear=False):
            return get_client_ip(request)

    def test_forwarded_header_is_ignored_by_default(self):
        self.assertEqual(
            self.get_ip(0, request_with_ip(forwarded_for="bad-ip")),
            "127.0.0.1",
        )

    def test_trusted_proxy_count_selects_client_from_rightmost_chain(self):
        request = request_with_ip(forwarded_for="198.51.100.9, 203.0.113.8")
        self.assertEqual(self.get_ip(1, request), "203.0.113.8")

    def test_malformed_forwarded_ip_is_rejected_when_proxy_trust_is_enabled(self):
        with self.assertRaises(HTTPException) as raised:
            self.get_ip(1, request_with_ip(forwarded_for="not-an-ip, 10.0.0.1"))
        self.assertEqual(raised.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
