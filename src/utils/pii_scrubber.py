import re
from typing import Iterable


EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

PHONE_REGEXES: Iterable[re.Pattern[str]] = (
    # Indian mobile numbers with optional country code
    re.compile(r"(?:\+91[- ]?)?[6-9]\d{9}"),
    # Generic international numbers with at least 10 digits
    re.compile(r"\b(?:\+?\d[\d\- ]{8,}\d)\b"),
)

AADHAAR_LIKE_REGEX = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")

# Basic URL detection (http/https and bare domains)
URL_REGEX = re.compile(
    r"(https?://\S+|\bwww\.[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b)",
    flags=re.IGNORECASE,
)

# Rough emoji range removal: covers common emoji blocks
EMOJI_REGEX = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "]+"
)


def _replace_all(pattern: re.Pattern[str], text: str, replacement: str) -> str:
    return pattern.sub(replacement, text)


def scrub_text(text: str) -> str:
    """Remove obvious PII, URLs, and emojis from free form text."""
    cleaned = _replace_all(EMAIL_REGEX, text, "[email removed]")
    for regex in PHONE_REGEXES:
        cleaned = _replace_all(regex, cleaned, "[phone removed]")
    cleaned = _replace_all(AADHAAR_LIKE_REGEX, cleaned, "[id removed]")
    cleaned = _replace_all(URL_REGEX, cleaned, "")
    cleaned = _replace_all(EMOJI_REGEX, cleaned, "")
    return cleaned.strip()

