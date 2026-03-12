"""
Email builder: convert markdown pulse note to HTML email body (Phase 5).
"""

import re
from typing import Optional

try:
    import markdown
except ImportError:
    markdown = None  # type: ignore


def build_subject(date_range: str) -> str:
    """Subject line: Groww Weekly Review Pulse: {date_range}."""
    return f"Groww Weekly Review Pulse: {date_range}"


def markdown_to_html(md: str) -> str:
    """Convert markdown to HTML with simple inline styles for email clients."""
    if markdown is not None:
        try:
            html_body = markdown.markdown(md, extensions=["nl2br", "sane_lists"])
        except Exception:
            html_body = markdown.markdown(md)
    else:
        html_body = _markdown_to_html_fallback(md)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.5; color: #333; max-width: 640px;">
{html_body}
</body>
</html>"""


def _markdown_to_html_fallback(md: str) -> str:
    """Minimal markdown to HTML without the markdown library."""
    html = md
    # Headers
    html = re.sub(r"^### (.+)$", r"<h3 style='margin-top:1em;'>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2 style='margin-top:1em;'>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1 style='margin-top:0;'>\1</h1>", html, flags=re.MULTILINE)
    # Bold
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    # Blockquotes
    html = re.sub(r"^> (.+)$", r"<blockquote style='margin:0.5em 0; padding-left:1em; border-left:4px solid #ccc;'>\1</blockquote>", html, flags=re.MULTILINE)
    # Paragraphs (double newline)
    parts = re.split(r"\n\n+", html)
    wrapped = []
    for p in parts:
        p = p.strip()
        if not p or p.startswith("<"):
            wrapped.append(p)
        else:
            wrapped.append(f"<p style='margin:0.5em 0;'>{p}</p>")
    return "\n".join(wrapped)


def build_email_html(body_markdown: str) -> str:
    """Build full HTML email body from markdown pulse content."""
    return markdown_to_html(body_markdown)
