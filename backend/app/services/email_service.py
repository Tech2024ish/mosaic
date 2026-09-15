import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_verification_email(email: str, name: str, token: str) -> None:
    settings = get_settings()
    verification_url = f"{settings.backend_url.rstrip('/')}/api/v1/auth/verify-email?token={token}"
    message = EmailMessage()
    message["Subject"] = "Verify your MOSAIC email address"
    message["From"] = settings.smtp_from_email
    message["To"] = email
    message.set_content(
        f"Hello {name},\n\nVerify your MOSAIC email address by opening:\n{verification_url}\n\n"
        f"This link expires in {settings.email_verification_expire_minutes} minutes."
    )
    if not settings.smtp_host:
        logger.info(
            "Email verification link generated",
            extra={"event_name": "email_verification_generated", "recipient": email},
        )
        logger.warning("SMTP is not configured; verification email was not sent")
        return
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
