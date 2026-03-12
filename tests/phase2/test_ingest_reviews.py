import sys
import types
from datetime import datetime
from pathlib import Path

import json

from src.config import load_config


def _install_dummy_google_play_scraper(monkeypatch):
    dummy_module = types.ModuleType("google_play_scraper")

    class DummySort:
        NEWEST = "NEWEST"

    def dummy_reviews(app_id, lang, country, sort, count):
        now = datetime(2026, 3, 10)
        result = [
            {
                "reviewId": "r1",
                "score": 5,
                "content": "Great app for investing.",
                "at": now,
                "thumbsUpCount": 10,
                "userLocale": "en_IN",
            },
            {
                "reviewId": "r2",
                "score": 1,
                "content": "Bad.",
                "at": now,
                "thumbsUpCount": 0,
                "userLocale": "hi_IN",
            },
        ]
        return result, None

    dummy_module.Sort = DummySort  # type: ignore[attr-defined]
    dummy_module.reviews = dummy_reviews  # type: ignore[attr-defined]

    sys.modules["google_play_scraper"] = dummy_module


def test_ingest_reviews_writes_json(monkeypatch, tmp_path):
    # Point data path to a temp directory
    data_dir = tmp_path / "data" / "reports" / "reviews"
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / "reviews.json"

    from src.phases.phase2 import ingest_reviews as ingest_module

    monkeypatch.setattr(ingest_module, "DATA_PATH", target)
    _install_dummy_google_play_scraper(monkeypatch)

    # Ensure config is loaded (uses defaults for app id, weeks, etc.)
    cfg = load_config()
    assert cfg.reviews.app_id

    reviews_list, summary = ingest_module.run()

    # We should have ingested at least the English review
    assert len(reviews_list) >= 1
    assert any(r.language and str(r.language).startswith("en") for r in reviews_list)

    assert summary["total_reviews"] == len(reviews_list)

    # Check JSON file exists and has reviews array
    assert target.exists()
    with target.open("r", encoding="utf-8") as f:
        data = json.load(f)

    assert "reviews" in data
    assert isinstance(data["reviews"], list)
    assert len(data["reviews"]) == len(reviews_list)

