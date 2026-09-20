import json
import logging
from dataclasses import asdict, is_dataclass
from typing import Any

from backend.aws_client import sqs
from backend.config import SQS_DISCOVERY_QUEUE_URL, SQS_ENABLED


logger = logging.getLogger(__name__)


def _serialize(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    return value


def enqueue_discovery_jobs(
    jobs: list[Any],
    run_id: str | None,
    profile: dict[str, Any],
    *,
    client=sqs,
    enabled: bool = SQS_ENABLED,
    queue_url: str | None = SQS_DISCOVERY_QUEUE_URL,
) -> dict[str, int]:
    """Publish minimal discovery envelopes for an optional async processor."""

    result = {"enabled": int(enabled), "enqueued": 0, "failures": 0}
    if not enabled or not queue_url:
        return result

    for job in jobs:
        try:
            client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps({
                    "run_id": run_id,
                    "job": _serialize(job),
                    "profile": profile,
                }, separators=(",", ":")),
            )
            result["enqueued"] += 1
        except Exception:
            result["failures"] += 1
            logger.exception("Discovery SQS enqueue failed", extra={"run_id": run_id})
    return result
