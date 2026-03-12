"""
FastAPI server for Web UI (Phase 7): trigger pipeline, status, latest run, send email.
Run: uvicorn src.api.server:app --reload --port 8000
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.pipeline import PipelineConfig, RunResult, run_pipeline

app = FastAPI(
    title="Groww Weekly Review Pulse API",
    description="Trigger pulse generation and email, get run status and latest report.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "status": "ok",
        "message": "Groww Weekly Review Pulse API. See /api/health for health check.",
    }

# In-memory store: run_id -> RunResult (for synchronous runs)
_runs: Dict[str, RunResult] = {}
_latest_run_id: Optional[str] = None
OUTPUT_BASE = Path("output")
RUN_RESULT_FILENAME = "run_result.json"
RUNS_INDEX_FILENAME = "runs.json"
REVIEWS_PATH = Path("data/reports/reviews/reviews.json")
PULSE_TEXT_PATH = Path("data/reports/pulse.txt")


class RunRequest(BaseModel):
    weeks: Optional[int] = None
    send_email: bool = False
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    force: bool = False


class SendEmailRequest(BaseModel):
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    force: bool = False


def _load_run_result(output_dir: Path) -> Optional[Dict[str, Any]]:
    path = output_dir / RUN_RESULT_FILENAME
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _find_latest_output_dir() -> Optional[Path]:
    """
    Find the most recent output directory that has a run_result.json.
    Prefer the runs index if present, fall back to filesystem scan.
    """
    index_path = OUTPUT_BASE / RUNS_INDEX_FILENAME
    if index_path.exists():
        try:
            runs = json.loads(index_path.read_text(encoding="utf-8"))
            if isinstance(runs, list) and runs:
                # runs are stored newest first by pipeline
                latest = runs[0]
                out = latest.get("output_dir")
                if out:
                    path = Path(out)
                    if path.exists():
                        return path
        except Exception:
            # fall back to directory scan
            pass
    if not OUTPUT_BASE.exists():
        return None
    dirs = [d for d in OUTPUT_BASE.iterdir() if d.is_dir()]
    if not dirs:
        return None
    dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    for d in dirs:
        if (d / RUN_RESULT_FILENAME).exists():
            return d
    return dirs[0] if dirs else None


@app.post("/api/pulse/run")
def api_pulse_run(body: RunRequest) -> Dict[str, Any]:
    """Trigger a new pipeline run. Returns run_id and status."""
    config = PipelineConfig(
        weeks=body.weeks,
        send_email=body.send_email,
        recipient_name=body.recipient_name,
        recipient_email=body.recipient_email,
        force=body.force,
    )
    result = run_pipeline(config)
    _runs[result.run_id] = result
    global _latest_run_id
    _latest_run_id = result.run_id
    return {
        "run_id": result.run_id,
        "status": result.status,
        "output_dir": result.output_dir,
        "error": result.error,
        "email_sent": result.email_sent,
    }


@app.get("/api/pulse/status/{run_id}")
def api_pulse_status(run_id: str) -> Dict[str, Any]:
    """Return status and summary for a run."""
    if run_id in _runs:
        r = _runs[run_id]
        return r.to_dict()
    # Try to find in output dirs
    if not OUTPUT_BASE.exists():
        raise HTTPException(status_code=404, detail="Run not found")
    for d in OUTPUT_BASE.iterdir():
        if not d.is_dir():
            continue
        data = _load_run_result(d)
        if data and data.get("run_id") == run_id:
            return data
    raise HTTPException(status_code=404, detail="Run not found")


@app.get("/api/pulse/latest")
def api_pulse_latest() -> Dict[str, Any]:
    """Return metadata for the latest run and link to one-pager."""
    out_dir = _find_latest_output_dir()
    if _latest_run_id and _latest_run_id in _runs:
        r = _runs[_latest_run_id]
        payload = r.to_dict()
        # Prefer plain text pulse for UI, fall back to markdown versions
        if PULSE_TEXT_PATH.exists():
            payload["pulse_content"] = PULSE_TEXT_PATH.read_text(encoding="utf-8")
        else:
            pulse_path = Path(r.pulse_path) if r.pulse_path else (
                Path(r.output_dir) / "weekly-pulse.md"
            )
            if pulse_path.exists():
                payload["pulse_content"] = pulse_path.read_text(encoding="utf-8")
            else:
                data_reports_md = Path("data/reports/pulse.md")
                payload["pulse_content"] = (
                    data_reports_md.read_text(encoding="utf-8")
                    if data_reports_md.exists()
                    else None
                )
        return payload
    if out_dir:
        data = _load_run_result(out_dir)
        if data:
            if PULSE_TEXT_PATH.exists():
                data["pulse_content"] = PULSE_TEXT_PATH.read_text(encoding="utf-8")
            else:
                pulse_path = out_dir / "weekly-pulse.md"
                if pulse_path.exists():
                    data["pulse_content"] = pulse_path.read_text(encoding="utf-8")
                else:
                    md = Path("data/reports/pulse.md")
                    data["pulse_content"] = (
                        md.read_text(encoding="utf-8") if md.exists() else None
                    )
            return data
    return {
        "run_id": None,
        "status": "not_run",
        "message": "No run yet. Trigger a run with POST /api/pulse/run",
    }


@app.post("/api/pulse/latest/email")
def api_pulse_latest_email(body: SendEmailRequest) -> Dict[str, Any]:
    """Send email for the latest run (or with given recipient)."""
    from src.phases.phase5.email_delivery import run as run_phase5
    out_dir = _find_latest_output_dir()
    if not out_dir and not _latest_run_id:
        raise HTTPException(
            status_code=400, detail="No latest run. Generate a pulse first."
        )

    # Load latest run metadata to respect email_sent flag
    latest_meta: Optional[Dict[str, Any]] = None
    index_path = OUTPUT_BASE / RUNS_INDEX_FILENAME
    if index_path.exists():
        try:
            runs = json.loads(index_path.read_text(encoding="utf-8"))
            if isinstance(runs, list) and runs:
                latest_meta = runs[0]
        except Exception:
            latest_meta = None

    if (
        latest_meta
        and latest_meta.get("email_sent")
        and not body.force
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Email already sent for latest run. "
                "Pass force=true in body to re-send."
            ),
        )
    recipient_email = body.recipient_email
    recipient_name = body.recipient_name
    r = run_phase5(
        recipient_name=recipient_name,
        recipient_email=recipient_email,
        send=True,
        output_dir=out_dir,
    )
    return {"sent": r["sent"], "to_address": r.get("to_address")}


@app.get("/api/files/latest-eml")
def api_files_latest_eml() -> Response:
    """
    Download the latest draft email .eml file for the most recent run.
    """
    out_dir = _find_latest_output_dir()
    if not out_dir:
        raise HTTPException(status_code=404, detail="No runs found")
    eml_path = out_dir / "weekly-pulse-email.eml"
    if not eml_path.exists():
        raise HTTPException(status_code=404, detail="No draft email for latest run")
    return FileResponse(
        path=eml_path,
        media_type="message/rfc822",
        filename="weekly-pulse-email.eml",
    )


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/reviews/latest")
def api_reviews_latest(limit: int = 20) -> Dict[str, Any]:
    """
    Return the latest ingested reviews and summary from data/reports/reviews/reviews.json.
    """
    if not REVIEWS_PATH.exists():
        raise HTTPException(status_code=404, detail="No reviews found. Run the pipeline first.")
    try:
        payload = json.loads(REVIEWS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Failed to read reviews: {exc}") from exc

    reviews = payload.get("reviews") or []
    summary = payload.get("summary") or {}
    total = len(reviews)
    # show most recent first based on list order (already newest-first from scraper)
    limited = reviews[: max(limit, 0)]

    return {
        "total_reviews": total,
        "summary": summary,
        "reviews": limited,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
