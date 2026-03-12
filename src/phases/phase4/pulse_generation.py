"""
Phase 4: Generate weekly pulse note from themes and grouped reviews.

Uses the canonical pulse generator (src.generation.pulse_generator) per ARCHITECTURE.md:
- Reads data/reports/themes/themes.json
- Writes output/YYYY-MM-DD/weekly-pulse.md (primary)
- Also writes data/reports/pulse.txt and data/reports/pulse.md for convenience
- Optional recipient_name/recipient_email (e.g. from frontend): when set, writes
  a personalized email body (Hi {name}, ...) to data/reports/pulse-email.md
"""

from pathlib import Path
from typing import Any, Dict, Optional

from src.generation.pulse_generator import (
    generate_pulse,
    render_pulse_markdown,
    render_pulse_for_email,
)
from src.models.pulse import WeeklyPulse

THEMES_PATH = Path("data/reports/themes/themes.json")
PULSE_PATH = Path("data/reports/pulse.txt")
PULSE_MD_PATH = Path("data/reports/pulse.md")
PULSE_EMAIL_PATH = Path("data/reports/pulse-email.md")


def _format_pulse_plain(pulse: WeeklyPulse) -> str:
    """Plain text version for pulse.txt."""
    lines = [
        "Groww App: Weekly Review Pulse",
        "=" * 40,
        "",
        f"Period: {pulse.date_range}",
        f"Reviews analyzed: {pulse.total_reviews}",
        "",
        "--- Top 3 Themes ---",
        "",
    ]
    for i, t in enumerate(pulse.themes, 1):
        lines.append(f"{i}. {t['name']} ({t['review_count']} reviews, {t['sentiment']})")
        lines.append(f"   {t['description']}")
        lines.append("")
    lines.append("--- What Users Are Saying ---")
    lines.append("")
    for q in pulse.quotes:
        lines.append('  "' + q["text"] + '"')
        lines.append(f"  Rating: {q['rating']}/5")
        lines.append("")
    lines.append("--- Action Ideas ---")
    lines.append("")
    for i, a in enumerate(pulse.action_ideas, 1):
        lines.append(f"{i}. {a['title']}: {a['description']}")
        lines.append("")
    return "\n".join(lines).strip()


def run(
    recipient_name: Optional[str] = None,
    recipient_email: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run Phase 4: generate pulse via canonical generator, write reports outputs.

    Optional recipient_name: when provided (e.g. from frontend), the weekly pulse
    report is also written as a personalized email body to data/reports/pulse-email.md
    starting with "Hi {recipient_name},". recipient_email is accepted for API
    consistency; actual sending is done in the email phase using config.
    """
    pulse, md_path = generate_pulse(themes_path=THEMES_PATH)

    # Write data/reports/pulse.txt and pulse.md
    PULSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PULSE_PATH.write_text(_format_pulse_plain(pulse), encoding="utf-8")
    PULSE_MD_PATH.write_text(render_pulse_markdown(pulse), encoding="utf-8")

    result: Dict[str, Any] = {
        "pulse_path": str(PULSE_PATH),
        "pulse_md_path": str(PULSE_MD_PATH),
        "weekly_pulse_md_path": str(md_path),
        "top_themes": [t["name"] for t in pulse.themes],
        "total_reviews": pulse.total_reviews,
        "date_range": pulse.date_range,
    }

    # When recipient name is provided, write personalized email body for the report
    if recipient_name is not None and str(recipient_name).strip():
        email_body = render_pulse_for_email(pulse, recipient_name=recipient_name)
        PULSE_EMAIL_PATH.write_text(email_body, encoding="utf-8")
        result["pulse_email_path"] = str(PULSE_EMAIL_PATH)
    result["recipient_name"] = (recipient_name or "").strip() or None
    result["recipient_email"] = (recipient_email or "").strip() or None

    return result


if __name__ == "__main__":
    run()
