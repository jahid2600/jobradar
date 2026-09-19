from backend.notifications import notify_new_opportunities
from backend.pipeline import run_pipeline
from backend.storage.dynamodb_job_store import PersistenceReport
from backend.discovery.job_schema import Job


def opportunity(title="AWS Cloud Engineer", company="Example Cloud"):
    return {
        "job": Job(
            title=title,
            company=company,
            location="Bengaluru",
            url=f"https://example.com/{title.replace(' ', '-').lower()}",
            source="tavily",
            description="AWS cloud role for a fresher with Linux.",
            experience="0-1 years",
        ),
        "qualification": {"qualified": True, "relevance_score": 88},
    }


class FakeSNS:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def publish(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return {"MessageId": "message-1"}


def test_notifications_disabled_makes_no_sns_call():
    client = FakeSNS()

    result = notify_new_opportunities(
        [opportunity()],
        "run-1",
        client=client,
        enabled=False,
        topic_arn="arn:aws:sns:region:account:topic",
    )

    assert result == {"attempted": False, "enabled": False, "published": False, "error": None}
    assert client.calls == []


def test_zero_opportunities_makes_no_sns_call():
    client = FakeSNS()

    result = notify_new_opportunities(
        [],
        "run-1",
        client=client,
        enabled=True,
        topic_arn="arn:aws:sns:region:account:topic",
    )

    assert result["attempted"] is False
    assert client.calls == []


def test_multiple_opportunities_publish_one_grouped_message():
    client = FakeSNS()

    result = notify_new_opportunities(
        [opportunity(), opportunity("Junior DevOps Engineer", "Another Systems")],
        "run-42",
        client=client,
        enabled=True,
        topic_arn="arn:aws:sns:region:account:topic",
    )

    assert result["published"] is True
    assert len(client.calls) == 1
    message = client.calls[0]["Message"]
    assert "run-42" in message
    assert "New opportunities: 2" in message
    assert "AWS Cloud Engineer" in message
    assert "Another Systems" in message
    assert "https://example.com/" in message


def test_publish_failure_is_reported_without_raising():
    result = notify_new_opportunities(
        [opportunity()],
        "run-1",
        client=FakeSNS(RuntimeError("SNS unavailable")),
        enabled=True,
        topic_arn="arn:aws:sns:region:account:topic",
    )

    assert result["attempted"] is True
    assert result["published"] is False
    assert "SNS unavailable" in result["error"]


class QualifiedEngine:
    def evaluate(self, job, profile):
        return {
            "qualified": True,
            "relevance_score": 90,
            "reason": "match",
            "matched_requirements": [],
            "skill_gaps": [],
            "concerns": [],
        }


class ExistingService:
    def existing_identities(self):
        return set()


class Provider:
    def search(self, query):
        return [opportunity()["job"], opportunity("Junior DevOps Engineer", "Another Systems")["job"]]


def test_pipeline_notifies_only_successfully_persisted_items():
    notified = []

    def notify(items, run_id):
        notified.append((items, run_id))
        return {"attempted": True, "enabled": True, "published": True, "error": None}

    run = run_pipeline(
        provider_factory=Provider,
        strategy_factory=lambda profile: {"search_queries": ["AWS Cloud Engineer Bengaluru"]},
        qualification_engine=QualifiedEngine(),
        opportunity_service=ExistingService(),
        save_dynamodb=lambda results: PersistenceReport(saved=results[:1], failures=1),
        save_local=lambda results: None,
        notification_func=notify,
        run_id="run-99",
        return_details=True,
    )

    assert run.metrics["persisted_new"] == 1
    assert run.metrics["persistence_failures"] == 1
    assert len(notified) == 1
    assert len(notified[0][0]) == 1
    assert notified[0][1] == "run-99"


def test_notification_failure_does_not_fail_pipeline():
    def notify(items, run_id):
        raise RuntimeError("SNS delivery failed")

    run = run_pipeline(
        provider_factory=Provider,
        strategy_factory=lambda profile: {"search_queries": ["AWS Cloud Engineer Bengaluru"]},
        qualification_engine=QualifiedEngine(),
        opportunity_service=ExistingService(),
        save_dynamodb=lambda results: results,
        save_local=lambda results: None,
        notification_func=notify,
        run_id="run-failure-isolated",
        return_details=True,
    )

    assert run.metrics["persisted_new"] == 2
    assert run.notification["published"] is False
    assert "SNS delivery failed" in run.notification["error"]
    assert not any("notification" in failure.lower() for failure in run.failures)