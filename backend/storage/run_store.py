import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import MAX_RADAR_RUN_HISTORY, RADAR_RUNS_FILE


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_run(run_id: str) -> dict[str, Any]:
    timestamp = utc_now()
    return {
        "run_id": run_id,
        "status": "running",
        "current_stage": "generating_strategy",
        "stage_progress": None,
        "started_at": timestamp,
        "completed_at": None,
        "duration_ms": None,
        "metrics": {},
        "failures": [],
        "generated_query_count": 0,
        # Compatibility fields retained at the top level.
        "discovered": 0,
        "relevant": 0,
        "duplicates": 0,
        "new_opportunities": 0,
    }


class RadarRunStore:
    """Small persistent run store for local development and single-host API use."""

    def __init__(self, path: str | Path = RADAR_RUNS_FILE):
        self.path = Path(path)

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _write(self, runs: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_path = tempfile.mkstemp(
            prefix=f"{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(runs[:MAX_RADAR_RUN_HISTORY], handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

    def create(self, run_id: str) -> dict[str, Any]:
        run = new_run(run_id)
        runs = self._read()
        self._write([run, *runs])
        return run

    def get(self, run_id: str) -> dict[str, Any] | None:
        return next((run for run in self._read() if run.get("run_id") == run_id), None)

    def latest(self) -> dict[str, Any] | None:
        runs = self._read()
        return runs[0] if runs else None

    def list_recent(self) -> list[dict[str, Any]]:
        return self._read()[:MAX_RADAR_RUN_HISTORY]

    def update(self, run_id: str, **changes: Any) -> dict[str, Any]:
        runs = self._read()
        for index, run in enumerate(runs):
            if run.get("run_id") == run_id:
                run.update(changes)
                runs[index] = run
                self._write(runs)
                return run
        raise KeyError(f"Radar run not found: {run_id}")