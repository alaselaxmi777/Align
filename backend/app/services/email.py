import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import settings

logger = logging.getLogger("align.email")

def send_email(to_email: str, subject: str, text_body: str, html_body: str | None = None) -> bool:
    """
    Sends an email using configured SMTP settings.
    Returns True if sent successfully, False otherwise.
    """
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        logger.warning(
            "SMTP credentials not fully configured. Host=%s, User=%s. Skipping email dispatch to %s.",
            settings.smtp_host,
            settings.smtp_username,
            to_email,
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email or settings.smtp_username
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain"))
    if html_body:
        msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
        logger.info("Successfully sent email to %s with subject '%s'", to_email, subject)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s via SMTP (%s:%s): %s", to_email, settings.smtp_host, settings.smtp_port, exc)
        return False

def send_verification_email(to_email: str, verify_token: str) -> bool:
    subject = "ALIGN — Verify Your Email Address"
    text_body = (
        f"Hello,\n\n"
        f"Thank you for registering on ALIGN!\n\n"
        f"Your verification token is:\n{verify_token}\n\n"
        f"Best regards,\nALIGN Team"
    )
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: sans-serif; line-height: 1.6; color: #3D2933; padding: 20px; background: #FFF5F7;">
        <div style="background: #FFFFFF; border: 1px solid #F3D5DC; border-radius: 16px; padding: 24px; max-width: 500px; margin: 0 auto;">
            <h2 style="color: #E8A0B0; margin-top: 0;">Welcome to ALIGN!</h2>
            <p>Please use the following verification token to verify your account email:</p>
            <div style="background: #FFF0F3; border: 1px solid #F3D5DC; padding: 12px 18px; border-radius: 8px; font-family: monospace; font-size: 18px; font-weight: bold; letter-spacing: 2px; color: #3D2933; text-align: center; margin: 16px 0;">
                {verify_token}
            </div>
            <p style="font-size: 13px; color: #8B737D;">
                This token will expire in 24 hours.
            </p>
            <hr style="border: none; border-top: 1px solid #F3D5DC; margin: 20px 0;" />
            <p style="font-size: 11px; color: #8B737D; margin-bottom: 0;">ALIGN — Personalized Community and Experience Discovery</p>
        </div>
    </body>
    </html>
    """
    return send_email(to_email, subject, text_body, html_body)

def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    subject = "ALIGN — Password Reset Request"
    text_body = (
        f"Hello,\n\n"
        f"A password reset request was requested for your ALIGN account.\n\n"
        f"Your reset token is:\n{reset_token}\n\n"
        f"If you did not request this, you can safely ignore this email.\n\n"
        f"Best regards,\nALIGN Team"
    )
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: sans-serif; line-height: 1.6; color: #333; padding: 20px;">
        <h2 style="color: #6366f1;">ALIGN Password Reset</h2>
        <p>A password reset request was initiated for your account.</p>
        <p>Use the following token to reset your password:</p>
        <div style="background: #f1f5f9; padding: 12px 18px; border-radius: 8px; font-family: monospace; font-size: 16px; font-weight: bold; letter-spacing: 1px; display: inline-block;">
            {reset_token}
        </div>
        <p style="margin-top: 20px; font-size: 14px; color: #64748b;">
            This token will expire in 2 hours. If you did not make this request, you can safely ignore this message.
        </p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
        <p style="font-size: 12px; color: #94a3b8;">ALIGN — Personalized Community and Experience Discovery</p>
    </body>
    </html>
    """
    return send_email(to_email, subject, text_body, html_body)
