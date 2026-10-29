import unittest
from unittest.mock import patch

from fastapi import HTTPException

from support import asgi_request, main


class ReadinessTests(unittest.TestCase):
    def test_health_confirms_database_connectivity(self):
        with patch.object(main, "_ping_database", return_value=True) as ping:
            status, body = asgi_request(main.app, "GET", "/health")

        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})
        ping.assert_called_once_with()

    def test_health_returns_generic_503_when_database_check_fails(self):
        with patch.object(main, "_ping_database", side_effect=RuntimeError("private connection information")):
            status, body = asgi_request(main.app, "GET", "/health")

        self.assertEqual(status, 503)
        self.assertEqual(body, {"detail": "Application unavailable"})
        self.assertNotIn("private", str(body).lower())

    def test_ready_reports_success_at_expected_schema_revision(self):
        with patch.object(main, "check_schema_revision", return_value=(True, "head")) as check:
            status, body = asgi_request(main.app, "GET", "/ready")

        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ready"})
        check.assert_called_once_with(main.engine)

    def test_ready_returns_generic_response_when_database_is_unavailable(self):
        with patch.object(main, "check_schema_revision", return_value=(False, "unavailable")):
            status, body = asgi_request(main.app, "GET", "/ready")

        self.assertEqual(status, 503)
        self.assertEqual(body, {"detail": "Application unavailable"})
        self.assertNotIn("connection", str(body).lower())
        self.assertNotIn("private", str(body).lower())

    def test_ready_returns_generic_response_when_schema_is_stale_or_missing(self):
        for reason in ("missing", "private-revision-id"):
            with self.subTest(reason=reason), patch.object(
                main, "check_schema_revision", return_value=(False, reason)
            ):
                status, body = asgi_request(main.app, "GET", "/ready")
                self.assertEqual(status, 503)
                self.assertNotIn(reason, str(body))


if __name__ == "__main__":
    unittest.main()
