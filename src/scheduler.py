"""
Scheduler to trigger the full pipeline on a fixed weekly schedule.

Usage (from project root):

    python -m src.scheduler

It will:
- Wait until the next Sunday 3:35 PM India Standard Time (IST)
- Trigger run_pipeline with send_email=True so the pulse is emailed
- Repeat weekly

Scheduler logs are written to logs/scheduler.log.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.pipeline import PipelineConfig, run_pipeline


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "scheduler.log"

# IST is UTC+5:30
IST_OFFSET = timedelta(hours=5, minutes=30)


def _configure_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("scheduler")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers in case of reuse
    if not any(
        isinstance(h, logging.FileHandler)
        and h.baseFilename == str(LOG_FILE.resolve())
        for h in logger.handlers
    ):
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def _seconds_until_next_sunday_1535_ist(now_utc: datetime) -> int:
    """
    Compute seconds until the next Sunday 15:35 IST.

    - Convert current time to IST
    - Find the next Sunday at 15:35 IST
    - Convert back to UTC and return the delta in seconds
    """
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    now_ist = now_utc + IST_OFFSET

    # Days until Sunday (weekday: Monday=0 .. Sunday=6)
    days_until_sunday = (6 - now_ist.weekday()) % 7
    target_ist = now_ist + timedelta(days=days_until_sunday)
    target_ist = target_ist.replace(hour=15, minute=35, second=0, microsecond=0)

    # If we are already past this Sunday's 15:35 IST, schedule for next week
    if target_ist <= now_ist:
        target_ist += timedelta(days=7)

    target_utc = target_ist - IST_OFFSET
    seconds = (target_utc - now_utc).total_seconds()
    return max(int(seconds), 0)


def run_once(logger: logging.Logger) -> None:
    """Run a single pipeline execution and log its result."""
    logger.info("Starting scheduled pipeline run (send_email=True).")
    try:
        config = PipelineConfig(send_email=True)
        result = run_pipeline(config)
        logger.info(
            "Pipeline finished. run_id=%s status=%s period=%s total_reviews=%s email_sent=%s",
            result.run_id,
            result.status,
            result.period,
            result.total_reviews,
            result.email_sent,
        )
        if result.error:
            logger.error("Pipeline error: %s", result.error)
    except Exception as exc:  # defensive
        logger.exception("Scheduled pipeline run failed: %s", exc)


def main() -> None:
    logger = _configure_logging()
    logger.info("Scheduler started. Logs at %s", LOG_FILE.resolve())

    while True:
        now_utc = datetime.now(timezone.utc)
        wait_seconds = _seconds_until_next_sunday_1535_ist(now_utc)
        target_utc = now_utc + timedelta(seconds=wait_seconds)
        logger.info(
            "Next run scheduled at %s UTC (in %s seconds)",
            target_utc.isoformat(),
            wait_seconds,
        )
        time.sleep(wait_seconds)
        run_once(logger)


if __name__ == "__main__":
    main()

