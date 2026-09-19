import logging
from typing import Any

from backend.aws_client import sns
from backend.config import SNS_ENABLED, SNS_TOPIC_ARN


logger = logging.getLogger(__name__)


def _format_message(opportunities: list[dict[str, Any]], run_id: str | None) -> str:
    lines = [
        "JobRadar: new qualified opportunities",
        f"Run ID: {run_id or 'unknown'}",
        f"New opportunities: {len(opportunities)}",
        "",
    ]

    for index, result in enumerate(opportunities, start=1):
        job = result.get("job", {})
        qualification = result.get("qualification", {})
        get_job_value = (
            lambda name: job.get(name)
            if isinstance(job, dict)
            else getattr(job, name, None)
        )
        lines.extend([
            f"{index}. {get_job_value('title') or 'Untitled opportunity'}",
            f"   Company: {get_job_value('company') or 'Not identified'}",
            f"   Location: {get_job_value('location') or 'Not identified'}",
            f"   Relevance: {qualification.get('relevance_score', 'N/A')}",
            f"   URL: {get_job_value('url') or 'Not available'}",
        ])

    return "\n".join(lines)


def notify_new_opportunities(
    opportunities: list[dict[str, Any]],
    run_id: str | None,
    *,
    client: Any = sns,
    enabled: bool = SNS_ENABLED,
    topic_arn: str | None = SNS_TOPIC_ARN,
) -> dict[str, Any]:
    """Publish one grouped SNS notification, or safely no-op when disabled."""

    result = {
        "attempted": False,
        "enabled": enabled,
        "published": False,
        "error": None,
    }
    if not opportunities:
        return result
    if not enabled:
        logger.info("SNS notifications disabled", extra={"run_id": run_id})
        return result

    result["attempted"] = True
    if not topic_arn:
        result["error"] = "SNS_TOPIC_ARN is not configured."
        logger.warning("SNS notification skipped: topic is not configured", extra={"run_id": run_id})
        return result

    try:
        client.publish(
            TopicArn=topic_arn,
            Subject="JobRadar new opportunities",
            Message=_format_message(opportunities, run_id),
        )
        result["published"] = True
        logger.info(
            "SNS notification published",
            extra={"run_id": run_id, "opportunity_count": len(opportunities)},
        )
    except Exception as exc:
        result["error"] = str(exc)
        logger.exception("SNS notification failed", extra={"run_id": run_id})

    return result