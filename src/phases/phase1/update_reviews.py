import json
from pathlib import Path
from typing import Any, Dict, List

from src.utils.pii_scrubber import scrub_text


DATA_PATH = Path("data/reports/reviews/reviews.json")


def load_reviews() -> Dict[str, Any]:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_reviews(data: Dict[str, Any]) -> None:
    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _is_probably_english(text: str, non_ascii_threshold: float = 0.3) -> bool:
    """Heuristic: drop texts with a high proportion of non ASCII chars."""
    if not text:
        return False
    total = len(text)
    non_ascii = sum(1 for ch in text if ord(ch) > 127)
    return (non_ascii / total) <= non_ascii_threshold


def filter_and_scrub_reviews(reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    for review in reviews:
        text = str(review.get("text", "")).strip()
        # Remove reviews that are predominantly non English (other scripts)
        if not _is_probably_english(text):
            continue
        cleaned = scrub_text(text)
        # Drop reviews with fewer than 2 words after cleaning
        if len(cleaned.split()) < 2:
            continue
        # Only scrub text; do not drop duplicates
        review["text"] = cleaned
        filtered.append(review)
    return filtered


def run() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Reviews file not found at {DATA_PATH}")

    data = load_reviews()
    reviews = data.get("reviews", [])
    if not isinstance(reviews, list):
        raise ValueError("reviews field must be a list")

    updated_reviews = filter_and_scrub_reviews(reviews)
    data["reviews"] = updated_reviews
    save_reviews(data)


if __name__ == "__main__":
    run()

