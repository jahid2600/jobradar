import json
import logging
from typing import Any

from backend.discovery.job_schema import Job
from backend.intelligence.bedrock_qualification import BedrockQualificationEngine
from backend.intelligence.deduplication import job_identity_keys
from backend.notifications import notify_new_opportunities
from backend.services.opportunity_service import DynamoDBOpportunityService
from backend.storage.dynamodb_job_store import save_jobs_with_report


logger = logging.getLogger(__name__)


def job_from_message(payload: dict[str, Any]) -> Job:
    return Job(**payload["job"])


def process_discovery_message(
    payload: dict[str, Any],
    *,
    qualification_engine: Any | None = None,
    opportunity_service: Any | None = None,
    save_dynamodb=None,
    notify=None,
) -> dict[str, Any]:
    """Process one SQS discovery envelope for a Lambda/SQS event source."""

    run_id = payload.get("run_id")
    job = job_from_message(payload)
    job_identity_keys(job)
    profile = payload.get("profile") or {}
    engine = qualification_engine or BedrockQualificationEngine()
    qualification = engine.evaluate(job, profile)
    result = {"job": job, "qualification": qualification}
    if not qualification.get("qualified", False):
        return {"status": "not_qualified", "run_id": run_id}

    service = opportunity_service or DynamoDBOpportunityService()
    if service.existing_identities() & job_identity_keys(job):
        return {"status": "existing", "run_id": run_id}

    persistence = (save_dynamodb or save_jobs_with_report)([result])
    saved = persistence.saved if hasattr(persistence, "saved") else persistence or []
    if not saved:
        return {"status": "not_persisted", "run_id": run_id}

    notification = notify(saved, run_id) if notify else None
    return {
        "status": "persisted",
        "run_id": run_id,
        "notification": notification,
        "persisted": saved,
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    results = []
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        results.append(process_discovery_message(body))
    grouped = {}
    for result in results:
        if result.get("status") == "persisted":
            grouped.setdefault(result.get("run_id"), []).extend(result.get("persisted", []))
    for run_id, opportunities in grouped.items():
        notify_new_opportunities(opportunities, run_id)
    logger.info("Discovery queue batch processed", extra={"count": len(results)})
    return {"results": results}
