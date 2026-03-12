"""
Phase 5: Email drafting and delivery.
Reads the personalized pulse (pulse-email.md or builds from pulse + recipient name),
builds HTML, saves .eml to output/YYYY-MM-DD/, and optionally sends via SMTP.
"""

import os
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

from src.config import get_effective_recipient, load_config
from src.email.email_builder import build_email_html, build_subject
from src.email.email_sender import send_pulse_email

PULSE_EMAIL_PATH = Path("data/reports/pulse-email.md")
WEEKLY_PULSE_EMAIL_FILENAME = "weekly-pulse-email.eml"


def run(
    recipient_name: Optional[str] = None,
    recipient_email: Optional[str] = None,
    send: Optional[bool] = None,
    pulse_email_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run Phase 5: build email from pulse-email.md, save .eml, optionally send.

    recipient_name: used only for logging; body is already in pulse-email.md from Phase 4.
    recipient_email: To address (or use EMAIL_TO from env).
    send: if True, send via SMTP; default from SEND_EMAIL env or False.
    """
    path = pulse_email_path or PULSE_EMAIL_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Pulse email body not found: {path}. Run Phase 4 with recipient_name first."
        )
    body_markdown = path.read_text(encoding="utf-8")

    # Extract date range from body for subject
    date_range = "N/A"
    for line in body_markdown.splitlines():
        if line.strip().startswith("**Period:**"):
            date_range = line.replace("**Period:**", "").strip()
            break
    subject = build_subject(date_range)
    html_body = build_email_html(body_markdown)

    run_date = date.today()
    if output_dir is None:
        output_dir = Path("output") / run_date.isoformat()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    eml_path = output_dir / WEEKLY_PULSE_EMAIL_FILENAME

    to_addr = get_effective_recipient(recipient_email)
    cfg = load_config().email
    from_addr = cfg.email_from or cfg.smtp_user or ""

    eml_content = f"""From: {from_addr}
To: {to_addr or '(no recipient)'}
Subject: {subject}
MIME-Version: 1.0
Content-Type: text/html; charset="utf-8"

{html_body}"""
    eml_path.write_text(eml_content, encoding="utf-8")

    result: Dict[str, Any] = {
        "eml_path": str(eml_path),
        "subject": subject,
        "date_range": date_range,
        "recipient_name": (recipient_name or "").strip() or None,
        "recipient_email": (recipient_email or "").strip() or None,
        "to_address": to_addr,
        "sent": False,
    }

    do_send = send if send is not None else os.environ.get("SEND_EMAIL", "").lower() in ("true", "1", "yes")
    if do_send:
        if not to_addr:
            raise ValueError("Cannot send: no recipient. Set recipient_email or EMAIL_TO.")
        send_pulse_email(html_body, subject, recipient_email=recipient_email)
        result["sent"] = True

    return result


if __name__ == "__main__":
    import sys
    send_flag = "--send" in sys.argv
    r = run(recipient_name="Akash", recipient_email="akash7050075323@gmail.com", send=send_flag)
    print("eml_path:", r["eml_path"])
    print("sent:", r["sent"])
    print("to_address:", r["to_address"])
