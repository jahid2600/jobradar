"""AWS Lambda adapter entry point for EventBridge Scheduler."""

from typing import Any

from backend.config import RADAR_LOCK_ENABLED, RADAR_SCHEDULE_ENABLED


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Delegate a private Scheduler invocation to the shared radar execution path."""

    if not RADAR_SCHEDULE_ENABLED or not RADAR_LOCK_ENABLED:
        return {
            "status": "disabled",
            "reason": "schedule_or_lock_disabled",
        }

    from api import run_scheduled_radar

    return run_scheduled_radar()
