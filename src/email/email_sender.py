"""
Email sender: send pulse email via SMTP (Phase 5).
Uses get_effective_recipient(override) for To address; config for SMTP and From.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from src.config import get_effective_recipient, load_config


def send_pulse_email(
    html_body: str,
    subject: str,
    recipient_email: Optional[str] = None,
) -> None:
    """
    Send the weekly pulse email via SMTP.
    recipient_email: from frontend/API; if None, uses EMAIL_TO from env.
    """
    to_addr = get_effective_recipient(recipient_email)
    if not to_addr:
        raise ValueError("No recipient: set recipient_email or EMAIL_TO in .env")

    cfg = load_config().email
    if not cfg.smtp_user or not cfg.smtp_password:
        missing = []
        if not cfg.smtp_user:
            missing.append("SMTP_USER or EMAIL_FROM")
        if not cfg.smtp_password:
            missing.append("SMTP_PASSWORD or EMAIL_PASSWORD")
        raise ValueError(
            f"Missing in .env: {', '.join(missing)}. "
            "Set EMAIL_FROM (sender) and EMAIL_PASSWORD (Gmail App Password) to send email."
        )
    from_addr = cfg.email_from or cfg.smtp_user

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port) as server:
        server.starttls()
        server.login(cfg.smtp_user, cfg.smtp_password)
        server.sendmail(from_addr, [to_addr], msg.as_string())
