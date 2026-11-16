import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException, Request

from app.core.request_context import get_client_ip, rate_limit_key


def request_with_ip(remote_ip="127.0.0.1", headers=None):
    request_headers = [(key.lower().encode("ascii"), value.encode("ascii")) for key, value in (headers or {}).items()]
    return Request({
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "GET", "scheme": "http", "path": "/", "raw_path": b"/",
        "query_string": b"", "headers": request_headers,
        "client": (remote_ip, 1234), "server": ("testserver", 80),
    })


class RequestContextTests(unittest.TestCase):
    def get_ip(self, source, request):
        with patch.dict(os.environ, {"CLIENT_IP_SOURCE": source}, clear=False):
            return get_client_ip(request)

    def test_direct_uses_socket_ip_and_ignores_forwarded_headers(self):
        request = request_with_ip(headers={
            "X-Forwarded-For": "203.0.113.99",
            "X-Real-IP": "203.0.113.98",
            "CF-Connecting-IP": "203.0.113.97",
        })
        self.assertEqual(self.get_ip("direct", request), "127.0.0.1")

    def test_trusted_edge_accepts_ipv4_and_ipv6(self):
        self.assertEqual(self.get_ip("cf-connecting-ip", request_with_ip(headers={"CF-Connecting-IP": "198.51.100.9"})), "198.51.100.9")
        self.assertEqual(self.get_ip("cf-connecting-ip", request_with_ip(headers={"CF-Connecting-IP": "2001:db8::1"})), "2001:db8::1")

    def test_trusted_edge_rejects_missing_empty_invalid_and_non_single_ips(self):
        for value in (None, "", "not-an-ip", "203.0.113.1, 203.0.113.2", "host.example", "203.0.113.1\ninjected"):
            with self.subTest(value=value):
                headers = {} if value is None else {"CF-Connecting-IP": value}
                with self.assertRaises(HTTPException) as raised:
                    self.get_ip("cf-connecting-ip", request_with_ip(headers=headers))
                self.assertEqual(raised.exception.status_code, 400)

    def test_trusted_edge_rejects_duplicate_header_fields(self):
        request = request_with_ip()
        request.scope["headers"] = [
            (b"cf-connecting-ip", b"198.51.100.1"),
            (b"cf-connecting-ip", b"198.51.100.2"),
        ]
        with self.assertRaises(HTTPException):
            self.get_ip("cf-connecting-ip", request)

    def test_rate_limit_key_groups_ipv6_by_64_and_keeps_ipv4_exact(self):
        self.assertEqual(rate_limit_key("198.51.100.9"), "198.51.100.9")
        self.assertNotEqual(rate_limit_key("198.51.100.9"), rate_limit_key("198.51.100.10"))
        self.assertEqual(rate_limit_key("2001:db8:1:2::1"), "2001:db8:1:2::/64")
        self.assertEqual(rate_limit_key("2001:db8:1:2:ffff:ffff:ffff:ffff"), "2001:db8:1:2::/64")
        self.assertNotEqual(rate_limit_key("2001:db8:1:2::1"), rate_limit_key("2001:db8:1:3::1"))
        self.assertEqual(rate_limit_key("::ffff:198.51.100.9"), "198.51.100.9")

    def test_client_ip_keeps_full_ipv6_for_audit(self):
        request = request_with_ip(headers={"CF-Connecting-IP": "2001:db8:1:2::abcd"})
        self.assertEqual(self.get_ip("cf-connecting-ip", request), "2001:db8:1:2::abcd")

    def test_unknown_source_fails_clearly(self):
        with self.assertRaisesRegex(RuntimeError, "CLIENT_IP_SOURCE"):
            self.get_ip("x-forwarded-for", request_with_ip())


if __name__ == "__main__":
    unittest.main()
