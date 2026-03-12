import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from project root (parent of src/)
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")


@dataclass
class GroqConfig:
    api_key: str
    model: str = "llama-3.3-70b-versatile"
    max_tokens: int = 2048
    temperature: float = 0.2


@dataclass
class ReviewConfig:
    app_id: str = "com.nextbillion.groww"
    review_window_weeks: int = 16
    # Current constraint from product: we will download up to 200 reviews
    max_reviews: int = 200


@dataclass
class EmailConfig:
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    # Fallback when recipient is not provided by frontend/API
    email_to: Optional[str] = None


@dataclass
class RunConfig:
    """
    Request-level options (e.g. from frontend/API).
    When the frontend sends a recipient email and name, pass them here so the pipeline
    uses them for sending and personalization.
    """
    recipient_email: Optional[str] = None  # From frontend; overrides EMAIL_TO when set
    recipient_name: Optional[str] = None   # From frontend; used for "Hi {name}," in email body


@dataclass
class AppConfig:
    groq: GroqConfig
    reviews: ReviewConfig
    email: EmailConfig


def load_config() -> AppConfig:
    groq_cfg = GroqConfig(
        api_key=os.environ.get("GROQ_API_KEY", ""),
        model=os.environ.get("GROQ_MODEL", GroqConfig.model),
        max_tokens=int(os.environ.get("GROQ_MAX_TOKENS", GroqConfig.max_tokens)),
        temperature=float(os.environ.get("GROQ_TEMPERATURE", GroqConfig.temperature)),
    )

    review_cfg = ReviewConfig(
        app_id=os.environ.get("APP_ID", ReviewConfig.app_id),
        review_window_weeks=int(
            os.environ.get("REVIEW_WINDOW_WEEKS", ReviewConfig.review_window_weeks)
        ),
        max_reviews=int(os.environ.get("MAX_REVIEWS", ReviewConfig.max_reviews)),
    )

    email_cfg = EmailConfig(
        smtp_host=os.environ.get("SMTP_HOST", EmailConfig.smtp_host),
        smtp_port=int(os.environ.get("SMTP_PORT", EmailConfig.smtp_port)),
        smtp_user=os.environ.get("SMTP_USER") or os.environ.get("EMAIL_FROM"),
        smtp_password=os.environ.get("SMTP_PASSWORD") or os.environ.get("EMAIL_PASSWORD"),
        email_from=os.environ.get("EMAIL_FROM"),
        email_to=os.environ.get("EMAIL_TO"),
    )

    return AppConfig(groq=groq_cfg, reviews=review_cfg, email=email_cfg)


def get_effective_recipient(override: Optional[str] = None) -> Optional[str]:
    """
    Resolve the email recipient: request override (e.g. from frontend) or env fallback.
    Use this in the pipeline/email step so the frontend can pass recipient_email.
    """
    if override and override.strip():
        return override.strip()
    return load_config().email.email_to

