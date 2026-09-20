import json

from backend.discovery.job_schema import Job
from backend.queue_processing import lambda_handler
from backend.storage.dynamodb_job_store import PersistenceReport


def test_queue_lambda_groups_persisted_records_before_notification(monkeypatch):
    job = Job(
        title="AWS Cloud Engineer",
        company="Example Cloud",
        location="Bengaluru",
        url="https://example.com/job",
        source="sqs",
        description="AWS cloud role for a fresher.",
        experience="0-1 years",
    )
    notifications = []

    monkeypatch.setattr(
        "backend.queue_processing.BedrockQualificationEngine",
        lambda: type("Engine", (), {"evaluate": lambda self, job, profile: {
            "qualified": True,
            "relevance_score": 90,
            "reason": "match",
        }})(),
    )
    monkeypatch.setattr(
        "backend.queue_processing.DynamoDBOpportunityService",
        lambda: type("Existing", (), {"existing_identities": lambda self: set()})(),
    )
    monkeypatch.setattr(
        "backend.queue_processing.save_jobs_with_report",
        lambda results: PersistenceReport(saved=results),
    )
    monkeypatch.setattr(
        "backend.queue_processing.notify_new_opportunities",
        lambda opportunities, run_id: notifications.append((opportunities, run_id)),
    )

    event = {
        "Records": [
            {"body": json.dumps({"run_id": "run-1", "job": job.__dict__, "profile": {}})},
            {"body": json.dumps({"run_id": "run-1", "job": job.__dict__, "profile": {}})},
        ]
    }
    lambda_handler(event, None)

    assert len(notifications) == 1
    assert notifications[0][1] == "run-1"
    assert len(notifications[0][0]) == 2