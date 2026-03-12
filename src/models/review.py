from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Review:
    review_id: str
    rating: int
    text: str
    date: date
    thumbs_up_count: int = 0
    language: Optional[str] = None

