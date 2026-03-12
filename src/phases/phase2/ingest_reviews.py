import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from google_play_scraper import Sort, reviews  # type: ignore

from src.config import load_config
from src.models import Review
from src.utils.pii_scrubber import scrub_text


logger = logging.getLogger(__name__)

DATA_PATH = Path("data/reports/reviews/reviews.json")


def _fetch_reviews_from_play_store(
    app_id: str, max_reviews: int, weeks: int
) -> List[Dict[str, Any]]:
    """Fetch raw reviews from the Play Store using google-play-scraper."""
    # google-play-scraper caps count per call; our config already limits to 200.
    count = max_reviews
    result, _continuation_token = reviews(
        app_id,
        lang="en",
        sort=Sort.NEWEST,
        count=count,
    )

    if weeks <= 0:
        return result

    cutoff = datetime.utcnow() - timedelta(weeks=weeks)
    filtered: List[Dict[str, Any]] = []
    for r in result:
        at = r.get("at")
        if isinstance(at, datetime):
            if at >= cutoff:
                filtered.append(r)
        else:
            filtered.append(r)
    return filtered


def _to_model(raw: Dict[str, Any]) -> Review:
    at = raw.get("at")
    if isinstance(at, datetime):
        d = at.date()
    else:
        d = datetime.utcnow().date()

    text = str(raw.get("content", "")).strip()
    return Review(
        review_id=str(raw.get("reviewId", "")),
        rating=int(raw.get("score", 0)),
        text=scrub_text(text),
        date=d,
        thumbs_up_count=int(raw.get("thumbsUpCount", 0)),
        language=raw.get("userLocale"),
    )


def _summarize(reviews_list: List[Review]) -> Dict[str, Any]:
    total = len(reviews_list)
    ratings: Dict[int, int] = {}
    for r in reviews_list:
        ratings[r.rating] = ratings.get(r.rating, 0) + 1
    dates: List[datetime] = []
    for r in reviews_list:
        dates.append(datetime.combine(r.date, datetime.min.time()))
    if dates:
        start = min(dates).date().isoformat()
        end = max(dates).date().isoformat()
    else:
        start = None
        end = None
    return {
        "total_reviews": total,
        "rating_distribution": ratings,
        "date_range": {"start": start, "end": end},
    }


def _load_existing_metadata() -> Dict[str, Any]:
    if not DATA_PATH.exists():
        return {}
    try:
        with DATA_PATH.open("r", encoding="utf-8") as f:
            existing = json.load(f)
        if isinstance(existing, dict):
            return existing
        return {}
    except json.JSONDecodeError:
        return {}


def run(weeks: Optional[int] = None) -> Tuple[List[Review], Dict[str, Any]]:
    cfg = load_config()
    review_window_weeks = weeks if weeks is not None else cfg.reviews.review_window_weeks
    raw_reviews = _fetch_reviews_from_play_store(
        app_id=cfg.reviews.app_id,
        max_reviews=cfg.reviews.max_reviews,
        weeks=review_window_weeks,
    )

    reviews_list = [_to_model(r) for r in raw_reviews]
    summary = _summarize(reviews_list)

    # Persist as JSON into data/reports/reviews/reviews.json
    data = _load_existing_metadata()
    data.setdefault("phase", 2)
    data["name"] = "Review Ingestion Pipeline"
    data["description"] = (
        "Imported Groww Play Store reviews, scrubbed PII, and persisted clean data."
    )
    data["llm_provider"] = "Groq"
    data["reviews"] = [
        {
            "reviewId": r.review_id,
            "rating": r.rating,
            "text": r.text,
            "date": r.date.isoformat(),
            "thumbsUpCount": r.thumbs_up_count,
            "language": r.language,
        }
        for r in reviews_list
    ]
    data["summary"] = summary

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info("Saved %s reviews to %s", len(reviews_list), DATA_PATH)
    return reviews_list, summary


if __name__ == "__main__":
    run()

