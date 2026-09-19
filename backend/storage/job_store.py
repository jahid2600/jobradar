import json
from pathlib import Path
from typing import Any


STORE_PATH = Path("data/jobs.json")


def save_jobs(results: list[dict[str, Any]]) -> None:
    """Persist JobRadar results locally."""

    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)

    serializable = []

    for result in results:
        serializable.append({
            "job": result["job"].to_dict(),
            "qualification": result["qualification"],
        })

    STORE_PATH.write_text(
        json.dumps(serializable, indent=2),
        encoding="utf-8",
    )


def load_jobs() -> list[dict[str, Any]]:
    """Load previously persisted JobRadar results."""

    if not STORE_PATH.exists():
        return []

    return json.loads(
        STORE_PATH.read_text(encoding="utf-8")
    )
