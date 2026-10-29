import unittest
from unittest.mock import patch

from fastapi import HTTPException

from support import asgi_request, main


class ReadinessTests(unittest.TestCase):
    def test_liveness_is_independent_of_database_state(self):
        with patch.object(main, "check_schema_revision", side_effect=AssertionError("must not query DB")):
            status, body = asgi_request(main.app, "GET", "/health")

        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

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
