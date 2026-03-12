"""
Data model for the weekly pulse note (Phase 4).
"""

from dataclasses import dataclass
from typing import List, TypedDict


class PulseQuote(TypedDict):
    """A single user quote in the pulse; attributed to rating only (no PII)."""
    text: str
    rating: str  # e.g. "4" or "4/5"


class PulseThemeSummary(TypedDict):
    """Summary of one theme in the pulse (top 3)."""
    name: str
    description: str
    sentiment: str  # positive | negative | mixed
    review_count: int


class PulseActionIdea(TypedDict):
    """One action idea for the product team."""
    title: str
    description: str


@dataclass
class WeeklyPulse:
    """One-page weekly pulse: top 3 themes, 3 quotes, 3 action ideas."""

    date_range: str  # e.g. "2026-03-01 to 2026-03-09"
    total_reviews: int
    themes: List[PulseThemeSummary]  # exactly 3
    quotes: List[PulseQuote]        # exactly 3; attributed to rating only
    action_ideas: List[PulseActionIdea]  # exactly 3

    def __post_init__(self) -> None:
        if len(self.themes) != 3:
            raise ValueError("themes must have exactly 3 items")
        if len(self.quotes) != 3:
            raise ValueError("quotes must have exactly 3 items")
        if len(self.action_ideas) != 3:
            raise ValueError("action_ideas must have exactly 3 items")
