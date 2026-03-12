"""
Unit tests for Phase 4 pulse generator (ARCHITECTURE: mock Groq, validate structure, no PII).
"""

import json
import re
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.generation.pulse_generator import (
    WEEKLY_PULSE_FILENAME,
    collect_quote_candidates,
    generate_pulse,
    render_pulse_markdown,
    render_pulse_for_email,
    select_top_themes,
)
from src.models.pulse import WeeklyPulse


# Fixture: minimal themes.json structure
THEMES_FIXTURE = {
    "source": "data/reports/reviews/reviews.json",
    "total_reviews": 50,
    "sampled_reviews": 50,
    "themes": [
        {
            "name": "Bugs",
            "description": "Users report bugs.",
            "sentiment": "negative",
            "reviews": [
                {"reviewId": "r1", "rating": 2, "text": "App crashes often.", "date": "2026-03-01"},
                {"reviewId": "r2", "rating": 1, "text": "Please fix the login issue.", "date": "2026-03-02"},
            ],
        },
        {
            "name": "UI",
            "description": "Good interface.",
            "sentiment": "positive",
            "reviews": [
                {"reviewId": "r3", "rating": 5, "text": "Clean and easy to use.", "date": "2026-03-03"},
            ],
        },
        {
            "name": "Support",
            "description": "Support feedback.",
            "sentiment": "mixed",
            "reviews": [],
        },
    ],
}

# Groq mock response (line-based format)
GROQ_MOCK_RESPONSE = """QUOTE1: [1] | 2
QUOTE2: [2] | 1
QUOTE3: [3] | 5
ACTION1: Fix crashes | Investigate and fix crash reports.
ACTION2: Improve login | Address login flow issues.
ACTION3: Keep UI | Maintain current interface quality."""


@pytest.fixture
def themes_path(tmp_path):
    p = tmp_path / "themes.json"
    p.write_text(json.dumps(THEMES_FIXTURE, indent=2), encoding="utf-8")
    return p


@pytest.fixture
def mock_groq_client():
    client = MagicMock()
    client.chat_completion.return_value = MagicMock(content=GROQ_MOCK_RESPONSE)
    return client


def test_select_top_themes():
    themes = THEMES_FIXTURE["themes"]
    top = select_top_themes(themes, n=3)
    assert len(top) == 3
    # Bugs (2), UI (1), Support (0); negative first
    assert top[0]["name"] == "Bugs"
    assert top[1]["name"] == "UI"
    assert top[2]["name"] == "Support"


def test_collect_quote_candidates():
    themes = THEMES_FIXTURE["themes"]
    top = select_top_themes(themes, n=3)
    candidates = collect_quote_candidates(top)
    assert len(candidates) >= 2  # at least 2 with text >= 10 chars
    assert all("text" in c and "rating" in c for c in candidates)


def test_generate_pulse_structure(themes_path, tmp_path, mock_groq_client):
    pulse, md_path = generate_pulse(
        themes_path=themes_path,
        output_dir=tmp_path / "out",
        run_date=date(2026, 3, 10),
        groq_client=mock_groq_client,
    )
    assert isinstance(pulse, WeeklyPulse)
    assert len(pulse.themes) == 3
    assert len(pulse.quotes) == 3
    assert len(pulse.action_ideas) == 3
    assert pulse.total_reviews == 50
    assert pulse.date_range != "N/A"
    assert md_path == tmp_path / "out" / WEEKLY_PULSE_FILENAME
    assert md_path.exists()


def test_generate_pulse_markdown_content(themes_path, tmp_path, mock_groq_client):
    pulse, md_path = generate_pulse(
        themes_path=themes_path,
        output_dir=tmp_path / "out",
        groq_client=mock_groq_client,
    )
    content = md_path.read_text(encoding="utf-8")
    assert "# Groww App: Weekly Review Pulse" in content
    assert "**Period:**" in content
    assert "**Reviews analyzed:**" in content
    assert "## Top 3 Themes" in content
    assert "## What Users Are Saying" in content
    assert "## Action Ideas" in content
    for t in pulse.themes:
        assert t["name"] in content
    for q in pulse.quotes:
        assert q["text"] in content
        assert "Rating:" in content


def test_generate_pulse_no_pii_in_output(themes_path, tmp_path, mock_groq_client):
    """Output must not contain PII: email, phone, Aadhaar-like numbers."""
    pulse, md_path = generate_pulse(
        themes_path=themes_path,
        output_dir=tmp_path / "out",
        groq_client=mock_groq_client,
    )
    content = md_path.read_text(encoding="utf-8")
    # No email pattern
    assert not re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", content)
    # No Indian mobile (10 digits)
    assert not re.search(r"\b[6-9]\d{9}\b", content)
    # No 12-digit Aadhaar-like
    assert not re.search(r"\b\d{4}\s?\d{4}\s?\d{4}\b", content)


def test_weekly_pulse_validation():
    """WeeklyPulse enforces exactly 3 themes, 3 quotes, 3 action ideas."""
    themes = [{"name": "A", "description": "a", "sentiment": "positive", "review_count": 1}] * 3
    quotes = [{"text": "q", "rating": "5"}] * 3
    actions = [{"title": "T", "description": "D"}] * 3
    pulse = WeeklyPulse(
        date_range="2026-01-01 to 2026-01-07",
        total_reviews=10,
        themes=themes,
        quotes=quotes,
        action_ideas=actions,
    )
    assert len(pulse.themes) == 3 and len(pulse.quotes) == 3 and len(pulse.action_ideas) == 3

    with pytest.raises(ValueError, match="themes must have exactly 3"):
        WeeklyPulse(
            date_range="x",
            total_reviews=0,
            themes=themes[:2],
            quotes=quotes,
            action_ideas=actions,
        )
    with pytest.raises(ValueError, match="quotes must have exactly 3"):
        WeeklyPulse(
            date_range="x",
            total_reviews=0,
            themes=themes,
            quotes=quotes[:2],
            action_ideas=actions,
        )


def test_render_pulse_markdown():
    pulse = WeeklyPulse(
        date_range="2026-01-01 to 2026-01-07",
        total_reviews=42,
        themes=[
            {"name": "Theme A", "description": "Desc A", "sentiment": "positive", "review_count": 10},
            {"name": "Theme B", "description": "Desc B", "sentiment": "negative", "review_count": 5},
            {"name": "Theme C", "description": "Desc C", "sentiment": "mixed", "review_count": 3},
        ],
        quotes=[
            {"text": "Quote one", "rating": "5"},
            {"text": "Quote two", "rating": "3"},
            {"text": "Quote three", "rating": "4"},
        ],
        action_ideas=[
            {"title": "Action 1", "description": "Do thing one."},
            {"title": "Action 2", "description": "Do thing two."},
            {"title": "Action 3", "description": "Do thing three."},
        ],
    )
    md = render_pulse_markdown(pulse)
    assert "2026-01-01 to 2026-01-07" in md
    assert "42" in md
    assert "Theme A" in md and "Theme B" in md and "Theme C" in md
    assert "Quote one" in md and "Quote two" in md and "Quote three" in md
    assert "Action 1" in md and "Action 2" in md and "Action 3" in md


def test_render_pulse_for_email_personalized():
    pulse = WeeklyPulse(
        date_range="2026-01-01 to 2026-01-07",
        total_reviews=42,
        themes=[
            {"name": "Theme A", "description": "Desc A", "sentiment": "positive", "review_count": 10},
            {"name": "Theme B", "description": "Desc B", "sentiment": "negative", "review_count": 5},
            {"name": "Theme C", "description": "Desc C", "sentiment": "mixed", "review_count": 3},
        ],
        quotes=[
            {"text": "Quote one", "rating": "5"},
            {"text": "Quote two", "rating": "3"},
            {"text": "Quote three", "rating": "4"},
        ],
        action_ideas=[
            {"title": "Action 1", "description": "Do thing one."},
            {"title": "Action 2", "description": "Do thing two."},
            {"title": "Action 3", "description": "Do thing three."},
        ],
    )
    body = render_pulse_for_email(pulse, recipient_name="Priya")
    assert body.startswith("Hi Priya,\n\n")
    assert "# Groww App: Weekly Review Pulse" in body
    assert "Theme A" in body
    body_no_name = render_pulse_for_email(pulse, recipient_name=None)
    assert body_no_name.startswith("Hi,\n\n")
    body_empty = render_pulse_for_email(pulse, recipient_name="  ")
    assert body_empty.startswith("Hi,\n\n")


def test_generate_pulse_no_themes_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="Themes file not found"):
        generate_pulse(
            themes_path=tmp_path / "nonexistent.json",
            output_dir=tmp_path,
        )


def test_generate_pulse_empty_themes(themes_path, tmp_path):
    empty = themes_path.parent / "empty_themes.json"
    empty.write_text(
        json.dumps({"themes": [], "total_reviews": 0}, indent=2),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="No themes"):
        generate_pulse(themes_path=empty, output_dir=tmp_path)
