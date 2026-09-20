import hashlib
import json
import logging
from dataclasses import asdict, is_dataclass
from typing import Any

from backend.aws_client import s3
from backend.config import (
    S3_RAW_DISCOVERY_BUCKET,
    S3_RAW_DISCOVERY_ENABLED,
    S3_RAW_DISCOVERY_PREFIX,
)
from backend.intelligence.deduplication import job_identity


logger = logging.getLogger(__name__)


def _safe_payload(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _safe_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_payload(item) for item in value]
    return value


def raw_object_key(run_id: str, job: Any) -> str:
    identity = job_identity(job)
    if not identity:
        identity = json.dumps(_safe_payload(job), sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return f"{S3_RAW_DISCOVERY_PREFIX}/{run_id}/{digest}.json"


def store_raw_discovery(
    run_id: str,
    payloads: list[Any],
    *,
    client=s3,
    enabled: bool = S3_RAW_DISCOVERY_ENABLED,
    bucket: str | None = S3_RAW_DISCOVERY_BUCKET,
) -> dict[str, Any]:
    """Store normalized discovery snapshots; disabled by default for local runs."""

    result = {"enabled": enabled, "stored": 0, "failures": 0}
    if not enabled or not bucket:
        return result

    for payload in payloads:
        try:
            key = raw_object_key(run_id, payload)
            body = json.dumps(_safe_payload(payload), separators=(",", ":"))
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=body.encode("utf-8"),
                ContentType="application/json",
                ServerSideEncryption="AES256",
            )
            result["stored"] += 1
        except Exception:
            result["failures"] += 1
            logger.exception("Raw discovery S3 write failed", extra={"run_id": run_id})

    return result
