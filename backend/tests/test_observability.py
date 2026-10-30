import unittest
from unittest.mock import patch

from support import Base, asgi_request, main
from app.core.observability import metrics_text, reset_metrics_for_tests


class ObservabilityTests(unittest.TestCase):
    def setUp(self):
        reset_metrics_for_tests()
        self.token = "observability-test-token-with-32-plus-characters"

    def tearDown(self):
        reset_metrics_for_tests()

    def test_metrics_count_routes_statuses_5xx_and_latency_without_ids(self):
        with patch.object(main, "_ping_database", return_value=True):
            status, _ = asgi_request(main.app, "GET", "/health")
        self.assertEqual(status, 200)
        with patch.object(main, "_ping_database", side_effect=RuntimeError("private connection detail")):
            status, _ = asgi_request(main.app, "GET", "/health")
        self.assertEqual(status, 503)

        with patch.object(main, "METRICS_TOKEN", self.token):
            status, body = asgi_request(
                main.app, "GET", "/metrics",
                headers={"Authorization": f"Bearer {self.token}"},
            )

        self.assertEqual(status, 200)
        self.assertIn('http_requests_total{route="/health",method="GET",status="200"} 1', body)
        self.assertIn('http_requests_total{route="/health",method="GET",status="503"} 1', body)
        self.assertIn("http_requests_5xx_ratio 0.500000", body)
        self.assertIn('quantile="0.50"', body)
        self.assertIn('quantile="0.95"', body)
        self.assertNotIn("private connection", body)

    def test_metrics_requires_token_and_is_disabled_when_not_configured(self):
        with patch.object(main, "METRICS_TOKEN", ""):
            status, _ = asgi_request(main.app, "GET", "/metrics")
        self.assertEqual(status, 404)
        with patch.object(main, "METRICS_TOKEN", self.token):
            status, body = asgi_request(main.app, "GET", "/metrics")
        self.assertEqual(status, 401)
        self.assertEqual(body, {"detail": "Invalid metrics credentials"})

    def test_metrics_use_route_templates_instead_of_resource_ids_or_query_values(self):
        Base.metadata.create_all(bind=main.engine)
        status, _ = asgi_request(
            main.app, "GET", "/services/987654321?email=private@example.test",
        )
        self.assertEqual(status, 404)
        exposition = metrics_text()
        self.assertIn('route="/services/{service_id}"', exposition)
        self.assertNotIn("987654321", exposition)
        self.assertNotIn("private@example.test", exposition)
        self.assertNotIn("email=", exposition)

    def test_request_logs_include_only_safe_route_metadata(self):
        request_id = "safe-request-id-123"
        authorization = "Bearer sensitive-auth-header"
        private_query = "customer@example.test"
        with patch.object(main, "_ping_database", return_value=True), self.assertLogs("app.request", level="INFO") as captured:
            status, _ = asgi_request(
                main.app, "GET", f"/health?email={private_query}",
                headers={"X-Request-ID": request_id, "Authorization": authorization},
            )

        self.assertEqual(status, 200)
        rendered = "\n".join(record.getMessage() for record in captured.records)
        self.assertIn('"request_id":"safe-request-id-123"', rendered)
        self.assertIn('"route":"/health"', rendered)
        self.assertIn('"status":200', rendered)
        self.assertIn('"duration_ms":', rendered)
        self.assertNotIn("email=", rendered)
        self.assertNotIn(private_query, rendered)
        self.assertNotIn(authorization, rendered)


if __name__ == "__main__":
    unittest.main()
