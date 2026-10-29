import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from app.config import settings as load_app_settings


class EmailDeliveryError(Exception):
    """Raised when a password reset message cannot be delivered."""


def send_password_reset_email(recipient: str, token: str) -> None:
    """Send a password reset link without exposing the token to application logs."""
    try:
        configuration = load_app_settings()
    except RuntimeError:
        raise EmailDeliveryError("Password reset email configuration is invalid") from None

    smtp_host = configuration.smtp_host
    reset_url = configuration.password_reset_url
    sender = configuration.smtp_from
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
    link = urlunsplit(parsed_url._replace(query=urlencode(query), fragment=urlencode({"token": token})))

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
        with smtplib.SMTP(
            smtp_host,
            configuration.smtp_port,
            timeout=configuration.smtp_timeout_seconds,
        ) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if configuration.smtp_username:
                smtp.login(configuration.smtp_username, configuration.smtp_password)
            smtp.send_message(message)
    except (OSError, ValueError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError("Password reset email could not be delivered") from exc
