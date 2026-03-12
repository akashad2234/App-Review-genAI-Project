"""
Pipeline orchestrator (Phase 6): ingest → filter → themes → pulse → email.
Exposes run_pipeline(config) for CLI and Web UI.
"""

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.phases.phase2.ingest_reviews import run as run_phase2
from src.phases.phase1.update_reviews import run as run_phase1
from src.phases.phase3.theme_generation import run as run_phase3
from src.phases.phase4.pulse_generation import run as run_phase4
from src.phases.phase5.email_delivery import run as run_phase5

logger = logging.getLogger(__name__)

OUTPUT_BASE = Path("output")
RUN_RESULT_FILENAME = "run_result.json"
RUNS_INDEX_FILENAME = "runs.json"


@dataclass
class PipelineConfig:
    weeks: Optional[int] = None
    send_email: bool = False
    output_dir: Optional[Path] = None
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    force: bool = False


@dataclass
class RunResult:
    run_id: str
    status: str  # "success" | "failed"
    started_at: str
    finished_at: str
    output_dir: str
    period: Optional[str] = None
    total_reviews: Optional[int] = None
    top_themes: List[str] = field(default_factory=list)
    pulse_path: Optional[str] = None
    eml_path: Optional[str] = None
    email_sent: bool = False
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _update_runs_index(result: RunResult) -> None:
    """
    Maintain a small runs index under output/runs.json so the Web UI
    and API can quickly discover recent runs without scanning dirs.
    """
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
    index_path = OUTPUT_BASE / RUNS_INDEX_FILENAME
    runs: List[Dict[str, Any]] = []
    if index_path.exists():
        try:
            runs = json.loads(index_path.read_text(encoding="utf-8"))
            if not isinstance(runs, list):
                runs = []
        except Exception:
            runs = []
    summary = {
        "run_id": result.run_id,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "status": result.status,
        "period": result.period,
        "total_reviews": result.total_reviews,
        "output_dir": result.output_dir,
        "email_sent": result.email_sent,
    }
    # replace if run_id already present, else append
    existing_idx = next(
        (i for i, r in enumerate(runs) if r.get("run_id") == result.run_id),
        None,
    )
    if existing_idx is not None:
        runs[existing_idx] = summary
    else:
        runs.append(summary)
    # sort by finished_at descending when available, else started_at
    def _ts(entry: Dict[str, Any]) -> str:
        return entry.get("finished_at") or entry.get("started_at") or ""
    runs.sort(key=_ts, reverse=True)
    index_path.write_text(json.dumps(runs, indent=2), encoding="utf-8")


def run_pipeline(config: PipelineConfig) -> RunResult:
    run_id = str(uuid.uuid4())[:8]
    started_at = datetime.utcnow().isoformat() + "Z"
    output_dir = config.output_dir or (OUTPUT_BASE / datetime.utcnow().strftime("%Y-%m-%d"))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = RunResult(
        run_id=run_id,
        status="failed",
        started_at=started_at,
        finished_at="",
        output_dir=str(output_dir),
    )

    try:
        # Phase 2: Ingest reviews from Play Store
        logger.info("Phase 2: Ingesting reviews (weeks=%s)", config.weeks)
        _, summary = run_phase2(weeks=config.weeks)
        result.period = (
            f"{summary.get('date_range', {}).get('start', '')} to {summary.get('date_range', {}).get('end', '')}"
            if summary.get("date_range")
            else None
        )
        result.total_reviews = summary.get("total_reviews")

        # Phase 1: Filter and scrub (uses data/reports/reviews/reviews.json)
        logger.info("Phase 1: Filter and scrub reviews")
        run_phase1()

        # Phase 3: Theme generation
        logger.info("Phase 3: Theme generation")
        phase3_out = run_phase3()
        result.top_themes = [t.get("name", "") for t in phase3_out.get("themes", [])][:5]

        # Phase 4: Pulse (with optional recipient for personalization)
        logger.info("Phase 4: Pulse generation")
        phase4_out = run_phase4(
            recipient_name=config.recipient_name,
            recipient_email=config.recipient_email,
        )
        result.pulse_path = phase4_out.get("weekly_pulse_md_path") or phase4_out.get("pulse_md_path")
        result.recipient_name = phase4_out.get("recipient_name")
        result.recipient_email = phase4_out.get("recipient_email")
        if phase4_out.get("total_reviews") is not None:
            result.total_reviews = phase4_out["total_reviews"]
        if phase4_out.get("date_range"):
            result.period = phase4_out["date_range"]

        # Phase 5: Email (draft + optional send)
        logger.info("Phase 5: Email draft and send")
        phase5_out = run_phase5(
            recipient_name=config.recipient_name,
            recipient_email=config.recipient_email,
            send=config.send_email,
            output_dir=output_dir,
        )
        result.eml_path = phase5_out.get("eml_path")
        result.email_sent = phase5_out.get("sent", False)

        result.status = "success"
    except Exception as e:
        logger.exception("Pipeline failed: %s", e)
        result.error = str(e)
        result.status = "failed"
    finally:
        result.finished_at = datetime.utcnow().isoformat() + "Z"
        run_result_path = output_dir / RUN_RESULT_FILENAME
        run_result_path.write_text(
            json.dumps(result.to_dict(), indent=2),
            encoding="utf-8",
        )
        _update_runs_index(result)

    return result
