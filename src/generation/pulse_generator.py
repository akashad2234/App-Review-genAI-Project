"""
Weekly pulse note generator (Phase 4 per ARCHITECTURE.md).

Takes themes + grouped reviews as input (from themes.json), calls Groq to select
3 impactful quotes and generate 3 action ideas, produces a one-page markdown pulse
at output/YYYY-MM-DD/weekly-pulse.md and returns a WeeklyPulse model.
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.llm.groq_client import GroqClient
from src.models.pulse import (
    PulseActionIdea,
    PulseQuote,
    PulseThemeSummary,
    WeeklyPulse,
)

DEFAULT_THEMES_PATH = Path("data/reports/themes/themes.json")
WEEKLY_PULSE_FILENAME = "weekly-pulse.md"


def _load_themes_data(themes_path: Path) -> Dict[str, Any]:
    if not themes_path.exists():
        raise FileNotFoundError(
            f"Themes file not found: {themes_path}. Run Phase 3 first."
        )
    with themes_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    themes = data.get("themes")
    if not isinstance(themes, list):
        raise ValueError("themes field must be a list")
    return data


def _date_range_from_themes(themes: List[Dict[str, Any]]) -> str:
    """Compute start_date to end_date from review dates in themes."""
    dates: List[date] = []
    for t in themes:
        for r in t.get("reviews") or []:
            d = r.get("date")
            if not d:
                continue
            if isinstance(d, str):
                try:
                    dates.append(date.fromisoformat(d[:10]))
                except ValueError:
                    continue
            elif hasattr(d, "year"):
                dates.append(d)
    if not dates:
        return "N/A"
    return f"{min(dates)} to {max(dates)}"


def select_top_themes(
    themes: List[Dict[str, Any]], n: int = 3
) -> List[Dict[str, Any]]:
    """Top n themes by review count; ties broken by negative sentiment first."""
    with_count = [(t, len(t.get("reviews") or [])) for t in themes]

    def key(item: Tuple[Dict, int]) -> Tuple[int, int]:
        t, count = item
        neg_first = 0 if (t.get("sentiment") == "negative") else 1
        return (-count, neg_first)

    with_count.sort(key=key)
    return [t for t, _ in with_count[:n]]


def collect_quote_candidates(
    top_themes: List[Dict[str, Any]],
    max_per_theme: int = 5,
    max_total: int = 20,
) -> List[Dict[str, Any]]:
    """PII-free quote candidates from top themes (one per theme where possible)."""
    candidates: List[Dict[str, Any]] = []
    for theme in top_themes:
        reviews = theme.get("reviews") or []
        for r in reviews[:max_per_theme]:
            text = (r.get("text") or "").strip()
            if len(text) < 10:
                continue
            candidates.append({
                "text": text[:300],
                "rating": r.get("rating"),
                "theme": theme.get("name", ""),
            })
        if len(candidates) >= max_total:
            break
    return candidates[:max_total]


def _build_pulse_prompt(
    top_themes: List[Dict[str, Any]],
    quote_candidates: List[Dict[str, Any]],
    total_reviews: int,
) -> List[Dict[str, str]]:
    themes_blob = "\n".join(
        f"- {t.get('name', '')} ({len(t.get('reviews') or [])} reviews, {t.get('sentiment', '')}): {t.get('description', '')}"
        for t in top_themes
    )
    quotes_blob = "\n".join(
        f"[{i+1}] (Theme: {c.get('theme', '')}, Rating: {c.get('rating')}/5) \"{c.get('text', '')}\""
        for i, c in enumerate(quote_candidates)
    )
    system = (
        "You are a product analyst for the Groww investing app. "
        "You create a concise weekly pulse from Play Store review themes and sample quotes."
    )
    user = f"""
We have analyzed {total_reviews} Groww app reviews and grouped them into themes. Here are the top 3 themes and candidate quotes.

Top 3 themes:
{themes_blob}

Candidate quotes (pick exactly 3 that are impactful and representative; prefer concrete feedback over vague complaints):
{quotes_blob}

Respond with exactly the following format. Use the candidate number [1], [2], etc. when referencing a quote. For action ideas, be concrete and actionable for the product team.

QUOTE1: [number] | rating
QUOTE2: [number] | rating
QUOTE3: [number] | rating
ACTION1: Short title | One sentence description
ACTION2: Short title | One sentence description
ACTION3: Short title | One sentence description
""".strip()
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _parse_pulse_response(
    response_text: str,
    quote_candidates: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    quotes: List[Dict[str, Any]] = []
    actions: List[Dict[str, str]] = []
    for line in response_text.splitlines():
        line = line.strip()
        if not line:
            continue
        upper = line.upper()
        if upper.startswith("QUOTE1:") or upper.startswith("QUOTE2:") or upper.startswith("QUOTE3:"):
            rest = line.split(":", 1)[-1].strip()
            parts = rest.split("|")
            num_part = parts[0].strip() if parts else ""
            rating_part = parts[1].strip() if len(parts) > 1 else ""
            match = re.search(r"\[?(\d+)\]?", num_part)
            idx = int(match.group(1)) - 1 if match else 0
            if 0 <= idx < len(quote_candidates):
                c = quote_candidates[idx]
                quotes.append({
                    "text": c.get("text", ""),
                    "rating": c.get("rating") or rating_part or "?",
                })
        elif upper.startswith("ACTION1:") or upper.startswith("ACTION2:") or upper.startswith("ACTION3:"):
            rest = line.split(":", 1)[-1].strip()
            if " | " in rest:
                title, desc = rest.split(" | ", 1)
                actions.append({"title": title.strip(), "description": desc.strip()})
            else:
                actions.append({"title": rest, "description": rest})
    while len(quotes) < 3 and quote_candidates:
        c = quote_candidates[min(len(quotes), len(quote_candidates) - 1)]
        quotes.append({"text": c.get("text", ""), "rating": str(c.get("rating", "?"))})
    while len(actions) < 3:
        actions.append({
            "title": "Review feedback",
            "description": "Prioritize based on theme volume and sentiment.",
        })
    return quotes[:3], actions[:3]


def render_pulse_markdown(pulse: WeeklyPulse) -> str:
    """Render WeeklyPulse to markdown per ARCHITECTURE template (public API)."""
    return _render_markdown(pulse)


def render_pulse_for_email(
    pulse: WeeklyPulse,
    recipient_name: Optional[str] = None,
) -> str:
    """
    Render the weekly pulse as email body with optional personalization.
    When recipient_name is provided (e.g. from frontend), the body starts with
    "Hi {name}," then a blank line, then the full pulse markdown.
    If recipient_name is missing or empty, uses "Hi,".
    """
    greeting = "Hi,"
    if recipient_name and recipient_name.strip():
        greeting = f"Hi {recipient_name.strip()},"  # no em dash per project rules
    body = _render_markdown(pulse)
    return f"{greeting}\n\n{body}"


def _render_markdown(pulse: WeeklyPulse) -> str:
    """Render WeeklyPulse to markdown per ARCHITECTURE template."""
    lines = [
        "# Groww App: Weekly Review Pulse",
        "",
        f"**Period:** {pulse.date_range}",
        f"**Reviews analyzed:** {pulse.total_reviews}",
        "",
        "---",
        "",
        "## Top 3 Themes",
        "",
    ]
    for i, t in enumerate(pulse.themes, 1):
        name = t["name"]
        count = t["review_count"]
        sentiment = t["sentiment"]
        desc = t["description"]
        lines.append(f"### {i}. {name} ({count} reviews, {sentiment})")
        lines.append("")
        lines.append(desc)
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## What Users Are Saying")
    lines.append("")
    for q in pulse.quotes:
        text = q["text"]
        rating = q["rating"]
        lines.append(f'> "{text}"')
        lines.append(f"> Rating: {rating}/5")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Action Ideas")
    lines.append("")
    for i, a in enumerate(pulse.action_ideas, 1):
        title = a["title"]
        desc = a["description"]
        lines.append(f"{i}. **{title}:** {desc}")
        lines.append("")
    return "\n".join(lines).strip()


def generate_pulse(
    themes_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    run_date: Optional[date] = None,
    groq_client: Optional[GroqClient] = None,
) -> Tuple[WeeklyPulse, Path]:
    """
    Load themes, select top 3, use Groq for quotes and action ideas, write weekly-pulse.md.

    Returns (WeeklyPulse, path_to_markdown_file).
    """
    themes_path = themes_path or DEFAULT_THEMES_PATH
    data = _load_themes_data(themes_path)
    themes = data.get("themes") or []
    total_reviews = data.get("total_reviews", 0)

    if not themes:
        raise ValueError("No themes in themes.json. Run Phase 3 first.")

    date_range = _date_range_from_themes(themes)
    top_themes = select_top_themes(themes, n=3)
    quote_candidates = collect_quote_candidates(top_themes)

    # Build theme summaries (exactly 3)
    theme_summaries: List[PulseThemeSummary] = [
        {
            "name": t.get("name", ""),
            "description": t.get("description", ""),
            "sentiment": t.get("sentiment", ""),
            "review_count": len(t.get("reviews") or []),
        }
        for t in top_themes
    ]

    if not quote_candidates:
        quotes: List[PulseQuote] = [
            {"text": "(No review quotes available)", "rating": "?"}
        ] * 3
        action_ideas: List[PulseActionIdea] = [
            {"title": "Review themes", "description": "Address top themes by volume and sentiment."},
            {"title": "Prioritize negatives", "description": "Focus on negative-sentiment themes first."},
            {"title": "Monitor next week", "description": "Track whether themes shift after changes."},
        ]
    else:
        messages = _build_pulse_prompt(top_themes, quote_candidates, total_reviews)
        client = groq_client or GroqClient()
        result = client.chat_completion(messages)
        raw_quotes, raw_actions = _parse_pulse_response(
            result.content, quote_candidates
        )
        quotes = [
            {"text": q.get("text", ""), "rating": str(q.get("rating", "?"))}
            for q in raw_quotes
        ]
        action_ideas = [
            {"title": a.get("title", ""), "description": a.get("description", "")}
            for a in raw_actions
        ]

    pulse = WeeklyPulse(
        date_range=date_range,
        total_reviews=total_reviews,
        themes=theme_summaries,
        quotes=quotes,
        action_ideas=action_ideas,
    )

    # Write output/YYYY-MM-DD/weekly-pulse.md
    run_date = run_date or date.today()
    if output_dir is None:
        output_dir = Path("output") / run_date.isoformat()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / WEEKLY_PULSE_FILENAME
    md_path.write_text(_render_markdown(pulse), encoding="utf-8")

    return pulse, md_path
