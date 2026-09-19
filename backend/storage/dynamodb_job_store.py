import logging
from dataclasses import dataclass, field
from typing import Any

from botocore.exceptions import ClientError

from backend.aws_client import dynamodb
from backend.config import DYNAMODB_TABLE_NAME
from backend.intelligence.deduplication import job_identity


logger = logging.getLogger(__name__)


@dataclass
class PersistenceReport:
    saved: list[dict[str, Any]] = field(default_factory=list)
    existing: int = 0
    failures: int = 0


def _is_conditional_duplicate(exc: Exception) -> bool:
    return isinstance(exc, ClientError) and exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"


def save_job(result: dict[str, Any], client=dynamodb) -> None:
    """Atomically insert one new opportunity using its logical identity key."""

    job = result["job"]
    qualification = result["qualification"]
    identity_key = job_identity(job)
    if not identity_key:
        raise ValueError("Opportunity has no stable persistence identity.")

    client.put_item(
        TableName=DYNAMODB_TABLE_NAME,
        ConditionExpression="attribute_not_exists(job_id)",
        Item={
            "job_id": {"S": identity_key},
            "identity_key": {"S": identity_key},
            "title": {"S": job.title},
            "company": {"S": job.company or ""},
            "location": {"S": job.location or ""},
            "url": {"S": job.url or ""},
            "source": {"S": job.source},
            "description": {"S": job.description or ""},
            "experience": {"S": job.experience or ""},
            "qualified": {"BOOL": qualification["qualified"]},
            "relevance_score": {"N": str(qualification["relevance_score"])},
            "reason": {"S": qualification["reason"]},
            "matched_requirements": {
                "L": [{"S": str(item)} for item in qualification.get("matched_requirements", [])],
            },
            "skill_gaps": {
                "L": [{"S": str(item)} for item in qualification.get("skill_gaps", [])],
            },
            "concerns": {
                "L": [{"S": str(item)} for item in qualification.get("concerns", [])],
            },
        },
    )


def save_jobs_with_report(results: list[dict[str, Any]], client=dynamodb) -> PersistenceReport:
    report = PersistenceReport()
    for result in results:
        try:
            save_job(result, client=client)
            report.saved.append(result)
        except Exception as exc:
            if _is_conditional_duplicate(exc):
                report.existing += 1
                logger.info("Opportunity already persisted", extra={"identity": job_identity(result["job"])})
            else:
                report.failures += 1
                logger.exception("Failed to persist opportunity", extra={"identity": job_identity(result["job"])})
    return report


def save_jobs(results: list[dict[str, Any]], client=dynamodb) -> list[dict[str, Any]]:
    """Legacy interface: return only successfully inserted opportunities."""

    return save_jobs_with_report(results, client=client).saved
