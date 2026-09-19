import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.pipeline import run_pipeline
from backend.services.opportunity_service import DynamoDBOpportunityService
from backend.storage.run_store import RadarRunStore, utc_now


logger = logging.getLogger(__name__)
app = FastAPI(title="JobRadar API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATUS_FILE = Path("data/latest_run.json")
run_store = RadarRunStore()
opportunity_service = DynamoDBOpportunityService()


def idle_run_status() -> dict[str, Any]:
    return {
        "run_id": None,
        "status": "idle",
        "current_stage": None,
        "stage_progress": None,
        "started_at": None,
        "completed_at": None,
        "duration_ms": None,
        "metrics": {},
        "failures": [],
        "generated_query_count": 0,
        "notification": {
            "attempted": False,
            "enabled": False,
            "published": False,
            "error": None,
        },
        "discovered": 0,
        "relevant": 0,
        "duplicates": 0,
        "new_opportunities": 0,
        "raw_discovered": 0,
        "filtered": 0,
        "unique": 0,
        "qualified": 0,
        "new_candidates": 0,
        "persisted_new": 0,
        "existing": 0,
        "persistence_failures": 0,
    }


def _compat_status(run: dict[str, Any]) -> dict[str, Any]:
    metrics = run.get("metrics") or {}
    return {
        **run,
        "discovered": metrics.get("raw_discovered", run.get("discovered", 0)),
        "relevant": metrics.get("qualified", run.get("relevant", 0)),
        "duplicates": metrics.get("duplicates", run.get("duplicates", 0)),
        "new_opportunities": metrics.get(
            "persisted_new",
            run.get("new_opportunities", 0),
        ),
    }


def _write_legacy_status(run: dict[str, Any]) -> None:
    try:
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATUS_FILE.write_text(json.dumps(_compat_status(run)), encoding="utf-8")
    except OSError:
        logger.exception("Could not mirror radar status to legacy status file", extra={"run_id": run.get("run_id")})


def _update_run(run_id: str, **changes: Any) -> dict[str, Any]:
    global latest_run
    run = run_store.update(run_id, **changes)
    _write_legacy_status(run)
    latest_run = _compat_status(run)
    return run


def _progress_callback(run_id: str):
    def update(stage: str, progress: int | None, metrics: dict[str, int], failures: list[str]):
        _update_run(
            run_id,
            status="running" if stage != "completed" else "completed",
            current_stage=stage,
            stage_progress=progress,
            metrics=metrics,
            failures=failures,
        )

    return update


def _current_run() -> dict[str, Any]:
    return _compat_status(run_store.latest() or idle_run_status())


# Compatibility for callers that imported the old process-local symbol.
latest_run = _current_run()


@app.get("/api/health")
def health():
    return {"status": "online", "service": "JobRadar API"}


def execute_radar(run_id: str) -> None:
    logger.info("Radar run started", extra={"run_id": run_id})
    try:
        run = run_pipeline(
            return_details=True,
            run_id=run_id,
            progress_callback=_progress_callback(run_id),
        )
        _update_run(
            run_id,
            status="completed",
            current_stage="completed",
            stage_progress=100,
            completed_at=utc_now(),
            duration_ms=run.metrics.get("duration_ms"),
            metrics=run.metrics,
            failures=run.failures,
            generated_query_count=run.generated_query_count,
            notification=run.notification,
        )
        logger.info("Radar run completed", extra={"run_id": run_id})
    except Exception as exc:
        logger.exception("Radar run failed", extra={"run_id": run_id})
        current = run_store.get(run_id) or {}
        failures = [*current.get("failures", []), str(exc)]
        started_at = current.get("started_at")
        duration_ms = None
        if started_at:
            try:
                started = started_at.replace("Z", "+00:00")
                duration_ms = round((datetime.now(timezone.utc) - datetime.fromisoformat(started)).total_seconds() * 1000)
            except ValueError:
                duration_ms = None
        _update_run(
            run_id,
            status="failed",
            current_stage="failed",
            stage_progress=None,
            completed_at=utc_now(),
            duration_ms=duration_ms,
            failures=failures,
        )


@app.get("/api/opportunities")
def opportunities():
    try:
        return opportunity_service.list_opportunities()
    except (BotoCoreError, ClientError):
        jobs_file = Path("data/jobs.json")
        if not jobs_file.exists():
            return []
        try:
            return json.loads(jobs_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []


@app.post("/api/radar/run")
def run_radar(background_tasks: BackgroundTasks):
    global latest_run
    current = run_store.latest()
    if current and current.get("status") == "running":
        return {
            "status": "running",
            "run_id": current.get("run_id"),
            "message": "Radar is already running.",
        }

    run_id = str(uuid.uuid4())
    run = run_store.create(run_id)
    latest_run = _compat_status(run)
    _write_legacy_status(run)
    background_tasks.add_task(execute_radar, run_id)

    return {
        "status": "started",
        "run_id": run_id,
        "message": "JobRadar scan started.",
    }


@app.get("/api/radar/status")
def radar_status():
    return _current_run()


@app.get("/api/radar/runs")
def radar_runs():
    return [_compat_status(run) for run in run_store.list_recent()]
