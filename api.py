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
from backend.config import RADAR_LOCK_ENABLED, RADAR_SCHEDULE_ENABLED
from backend.observability import publish_run_metrics
from backend.services.opportunity_service import DynamoDBOpportunityService
from backend.storage.radar_lock import RadarExecutionLock, LockLease
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
radar_lock = RadarExecutionLock()


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
        "trigger": {"type": "manual"},
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


def execute_radar(run_id: str, trigger_type: str = "manual", lease: LockLease | None = None) -> None:
    logger.info("Radar run started", extra={"run_id": run_id, "trigger": trigger_type})
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
            trigger={"type": trigger_type},
        )
        logger.info("Radar run completed", extra={"run_id": run_id, "trigger": trigger_type})
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
            trigger={"type": trigger_type},
        )
        publish_run_metrics(
            current.get("metrics", {}),
            success=False,
            notification_failure=False,
        )
    finally:
        if lease is not None:
            try:
                radar_lock.release(lease)
            except Exception:
                logger.exception("Radar lock release failed", extra={"run_id": run_id})


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
    if not RADAR_LOCK_ENABLED and current and current.get("status") == "running":
        return {
            "status": "running",
            "run_id": current.get("run_id"),
            "message": "Radar is already running.",
        }

    run_id = str(uuid.uuid4())
    lease = radar_lock.acquire(run_id) if RADAR_LOCK_ENABLED else None
    if RADAR_LOCK_ENABLED and not lease.acquired:
        current = run_store.latest() or {}
        return {
            "status": "running",
            "run_id": current.get("run_id"),
            "message": "Radar is already running.",
        }
    run = run_store.create(run_id)
    run["trigger"] = {"type": "manual"}
    run_store.update(run_id, trigger=run["trigger"])
    latest_run = _compat_status(run)
    _write_legacy_status(run)

    def execute_manual_run(_run_id: str):
        execute_radar(run_id, "manual", lease)

    # Keep the historical one-argument background task shape for local callers.
    background_tasks.add_task(execute_manual_run, run_id)

    return {
        "status": "started",
        "run_id": run_id,
        "message": "JobRadar scan started.",
    }


def run_scheduled_radar() -> dict[str, Any]:
    """Entry point for a private AWS-native scheduler adapter."""

    if not RADAR_SCHEDULE_ENABLED or not RADAR_LOCK_ENABLED:
        logger.info("Scheduled radar invocation ignored: scheduling disabled")
        return {"status": "disabled", "reason": "schedule_or_lock_disabled"}

    run_id = str(uuid.uuid4())
    lease = radar_lock.acquire(run_id) if RADAR_LOCK_ENABLED else None
    if RADAR_LOCK_ENABLED and not lease.acquired:
        logger.info("Scheduled radar invocation skipped: lock is held", extra={"run_id": run_id, "trigger": "scheduled"})
        return {"status": "skipped", "reason": "active_run"}

    run_store.create(run_id)
    run_store.update(run_id, trigger={"type": "scheduled"})
    execute_radar(run_id, "scheduled", lease)
    return {"status": "completed", "run_id": run_id}


@app.get("/api/radar/status")
def radar_status():
    return _current_run()


@app.get("/api/radar/runs")
def radar_runs():
    return [_compat_status(run) for run in run_store.list_recent()]
