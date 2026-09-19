from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from botocore.exceptions import BotoCoreError, ClientError
from backend.pipeline import run_pipeline
from backend.services.opportunity_service import DynamoDBOpportunityService
from pathlib import Path
import json

app = FastAPI(title="JobRadar API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATUS_FILE = Path("data/latest_run.json")


def idle_run_status():
    return {
        "status": "idle",
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
        "duration_ms": 0,
        "failures": [],
    }


def load_latest_run():
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text())
        except Exception:
            pass

    return idle_run_status()


def save_latest_run(data):
    STATUS_FILE.parent.mkdir(exist_ok=True)
    STATUS_FILE.write_text(json.dumps(data))


latest_run = load_latest_run()
opportunity_service = DynamoDBOpportunityService()
if latest_run.get("status") == "idle":
    latest_run = idle_run_status()


@app.get("/api/health")
def health():
    return {
        "status": "online",
        "service": "JobRadar API",
    }


def execute_radar():
    global latest_run

    latest_run["status"] = "running"
    save_latest_run(latest_run)

    try:
        run = run_pipeline(return_details=True)
        metrics = run.metrics

        latest_run = {
            "status": "completed",
            "discovered": metrics["raw_discovered"],
            "relevant": metrics["qualified"],
            "duplicates": metrics["duplicates"],
            "new_opportunities": metrics["persisted_new"],
            **metrics,
            "failures": run.failures,
        }

        save_latest_run(latest_run)

    except Exception as exc:
        latest_run = {
            "status": "error",
            "error": str(exc),
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
            "duration_ms": 0,
            "failures": [str(exc)],
        }

        save_latest_run(latest_run)


@app.get("/api/opportunities")
def opportunities():
    try:
        return opportunity_service.list_opportunities()
    except (BotoCoreError, ClientError):
        # Local JSON is retained only as a development/debug fallback when
        # DynamoDB is unavailable.
        jobs_file = Path("data/jobs.json")
        if not jobs_file.exists():
            return []

        try:
            return json.loads(jobs_file.read_text())
        except (OSError, json.JSONDecodeError):
            return []


@app.post("/api/radar/run")
def run_radar(background_tasks: BackgroundTasks):
    if latest_run["status"] == "running":
        return {
            "status": "running",
            "message": "Radar is already running.",
        }

    background_tasks.add_task(execute_radar)

    return {
        "status": "started",
        "message": "JobRadar scan started.",
    }


@app.get("/api/radar/status")
def radar_status():
    return latest_run
