import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl


logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Raised when a password reset message cannot be delivered."""


def send_password_reset_email(recipient: str, token: str) -> None:
    """Send a reset link, or expose the token only to an explicit local dev log."""
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    if not smtp_host and os.getenv("APP_ENV", "").strip().lower() == "development":
        logger.info("Local password reset token for %s: %s", recipient, token)
        return

    reset_url = os.getenv("PASSWORD_RESET_URL", "").strip()
    sender = os.getenv("SMTP_FROM", "").strip()
    if not smtp_host or not reset_url or not sender:
        raise EmailDeliveryError("Password reset email delivery is not configured")

    parsed_url = urlsplit(reset_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise EmailDeliveryError("PASSWORD_RESET_URL must be an absolute HTTP(S) URL")

    query = [
        (key, value)
        for key, value in parse_qsl(parsed_url.query, keep_blank_values=True)
        if key != "token"
    ]
    query.append(("token", token))
    link = urlunsplit(parsed_url._replace(query=urlencode(query)))

    message = EmailMessage()
    message["Subject"] = "Redefinição de senha"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "Use o link a seguir para redefinir sua senha. "
        "Ele é válido por uma hora e pode ser usado uma única vez:\n\n"
        f"{link}\n"
    )

    try:
        port = int(os.getenv("SMTP_PORT", "587"))
        timeout = float(os.getenv("SMTP_TIMEOUT_SECONDS", "10"))
        username = os.getenv("SMTP_USERNAME", "").strip()
        password = os.getenv("SMTP_PASSWORD", "")
        with smtplib.SMTP(smtp_host, port, timeout=timeout) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    except (OSError, ValueError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError("Password reset email could not be delivered") from exc
