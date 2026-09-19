from typing import Any

from backend.aws_client import dynamodb


TABLE_NAME = "jobradar-jobs"


def save_job(result: dict[str, Any]) -> None:
    """Save one JobRadar opportunity to DynamoDB."""

    job = result["job"]
    qualification = result["qualification"]

    dynamodb.put_item(
        TableName=TABLE_NAME,
        Item={
            "job_id": {
                "S": job.url,
            },
            "title": {
                "S": job.title,
            },
            "company": {
                "S": job.company or "",
            },
            "location": {
                "S": job.location or "",
            },
            "url": {
                "S": job.url,
            },
            "source": {
                "S": job.source,
            },
            "description": {
                "S": job.description or "",
            },
            "experience": {
                "S": job.experience or "",
            },
            "qualified": {
                "BOOL": qualification["qualified"],
            },
            "relevance_score": {
                "N": str(qualification["relevance_score"]),
            },
            "reason": {
                "S": qualification["reason"],
            },
        },
    )


def save_jobs(results: list[dict[str, Any]]) -> None:
    """Save multiple JobRadar opportunities to DynamoDB."""

    for result in results:
        save_job(result)
