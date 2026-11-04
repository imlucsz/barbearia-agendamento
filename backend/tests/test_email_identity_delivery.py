"""Transport capability checks without opening sockets or delivering messages.

Acceptance by a mocked transport does not establish mailbox deliverability.
"""
import json
import smtplib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from support import main  # Establish isolated settings before importing app modules.
from app.core.email import EmailDeliveryError, send_password_reset_email
from app.schemas.user import EsqueciSenhaRequest


class EmailIdentityDeliveryTests(unittest.TestCase):
    def configuration(self, transport="smtp"):
        return SimpleNamespace(
            email_transport=transport, smtp_host="smtp.example.test", smtp_port=587,
            smtp_timeout_seconds=1, smtp_from="sender@example.com", smtp_username="",
            smtp_password="", password_reset_url="https://example.test/reset",
            email_from="sender@example.com", email_timeout_seconds=1,
            brevo_api_key="test-only-placeholder",
        )

    def smtp_client(self, supports_utf8):
        # No host: constructing this real stdlib client does not connect.
        smtp = smtplib.SMTP()
        smtp.ehlo_or_helo_if_needed = MagicMock()
        smtp.starttls = MagicMock()
        smtp.has_extn = MagicMock(return_value=supports_utf8)
        smtp.sendmail = MagicMock(return_value={})
        smtp.quit = MagicMock(return_value=(221, b"bye"))
        return smtp

    def test_ascii_recipient_does_not_require_smtputf8(self):
        smtp = self.smtp_client(False)
        with patch("app.core.email.load_app_settings", return_value=self.configuration()), \
             patch("app.core.email.smtplib.SMTP", return_value=smtp):
            send_password_reset_email("person@example.com", "test-only-token")
        smtp.sendmail.assert_called_once()
        self.assertNotIn("SMTPUTF8", smtp.sendmail.call_args.args[3])

    def test_schema_accepted_international_addresses_need_smtputf8_on_current_smtp_path(self):
        for address in ["jos\u00e9@example.com", "person@xn--bcher-kva.de"]:
            recipient = EsqueciSenhaRequest(email=address).email
            smtp = self.smtp_client(False)
            with patch("app.core.email.load_app_settings", return_value=self.configuration()), \
                 patch("app.core.email.smtplib.SMTP", return_value=smtp):
                with self.assertRaises(EmailDeliveryError) as caught:
                    send_password_reset_email(recipient, "test-only-token")
            self.assertEqual(str(caught.exception), "Password reset email could not be delivered")
            smtp.sendmail.assert_not_called()
            smtp.has_extn.assert_called_with("smtputf8")

    def test_smtputf8_negotiation_uses_real_stdlib_serialization(self):
        for address in ["jos\u00e9@example.com", "person@xn--bcher-kva.de"]:
            recipient = EsqueciSenhaRequest(email=address).email
            smtp = self.smtp_client(True)
            with patch("app.core.email.load_app_settings", return_value=self.configuration()), \
                 patch("app.core.email.smtplib.SMTP", return_value=smtp):
                send_password_reset_email(recipient, "test-only-token")
            smtp.sendmail.assert_called_once()
            options = smtp.sendmail.call_args.args[3]
            self.assertIn("SMTPUTF8", options)
            self.assertIn("BODY=8BITMIME", options)
            self.assertTrue(smtp.sendmail.call_args.args[1] == [recipient])

    def test_brevo_preserves_unicode_payload_but_acceptance_is_not_delivery(self):
        for status in [201, 400]:
            connection = MagicMock()
            connection.getresponse.return_value.status = status
            recipient = EsqueciSenhaRequest(email="Jose\u0301@xn--bcher-kva.de").email
            with patch("app.core.email.load_app_settings", return_value=self.configuration("brevo_api")), \
                 patch("app.core.email.http.client.HTTPSConnection", return_value=connection):
                if status == 201:
                    send_password_reset_email(recipient, "test-only-token")
                else:
                    with self.assertRaises(EmailDeliveryError) as caught:
                        send_password_reset_email(recipient, "test-only-token")
                    self.assertEqual(str(caught.exception), "Password reset email could not be delivered")
            payload = json.loads(connection.request.call_args.kwargs["body"].decode("utf-8"))
            self.assertTrue(payload["to"] == [{"email": recipient}])
            connection.close.assert_called_once()
