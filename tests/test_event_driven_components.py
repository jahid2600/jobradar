import json

from backend.discovery.job_schema import Job
from backend.observability import publish_run_metrics
from backend.queueing import enqueue_discovery_jobs
from backend.storage.raw_discovery_store import raw_object_key, store_raw_discovery
from backend.discovery import tavily_search_provider


JOB = Job(
    title="AWS Cloud Engineer",
    company="Example Cloud",
    location="Bengaluru",
    url="https://example.com/jobs/1",
    source="tavily",
    description="AWS cloud role for a fresher.",
    experience="0-1 years",
)


def test_raw_s3_key_is_deterministic_and_disabled_is_safe():
    first = raw_object_key("run-1", JOB)
    second = raw_object_key("run-1", JOB)
    assert first == second

    class NeverCalled:
        def put_object(self, **kwargs):
            raise AssertionError("S3 should be disabled")

    result = store_raw_discovery("run-1", [JOB], client=NeverCalled(), enabled=False, bucket="bucket")
    assert result == {"enabled": False, "stored": 0, "failures": 0}


def test_raw_s3_payload_is_encrypted_and_stored():
    calls = []

    class FakeS3:
        def put_object(self, **kwargs):
            calls.append(kwargs)

    result = store_raw_discovery("run-1", [JOB], client=FakeS3(), enabled=True, bucket="bucket")

    assert result["stored"] == 1
    assert calls[0]["ServerSideEncryption"] == "AES256"
    assert json.loads(calls[0]["Body"].decode("utf-8"))["title"] == JOB.title


def test_sqs_envelope_contains_minimal_processing_data():
    calls = []

    class FakeSQS:
        def send_message(self, **kwargs):
            calls.append(kwargs)

    result = enqueue_discovery_jobs(
        [JOB],
        "run-1",
        {"location": "Bengaluru"},
        client=FakeSQS(),
        enabled=True,
        queue_url="https://sqs.example/queue",
    )

    assert result == {"enabled": 1, "enqueued": 1, "failures": 0}
    body = json.loads(calls[0]["MessageBody"])
    assert body["run_id"] == "run-1"
    assert body["job"]["url"] == JOB.url
    assert "description" in body["job"]


def test_cloudwatch_metrics_are_optional_and_structured():
    calls = []

    class FakeCloudWatch:
        def put_metric_data(self, **kwargs):
            calls.append(kwargs)

    publish_run_metrics(
        {"raw_discovered": 4, "qualified": 2, "persisted_new": 1},
        success=True,
        notification_failure=False,
        client=FakeCloudWatch(),
        enabled=True,
    )

    assert len(calls) == 1
    names = {item["MetricName"] for item in calls[0]["MetricData"]}
    assert {"RadarRunSuccess", "RawDiscovered", "Qualified", "PersistedNew"} <= names


def test_tavily_secret_lookup_uses_secret_manager_without_logging_value(monkeypatch):
    class FakeSecrets:
        def get_secret_value(self, **kwargs):
            return {"SecretString": '{"TAVILY_API_KEY":"secret-value"}'}

    monkeypatch.setattr(tavily_search_provider, "secretsmanager", FakeSecrets())
    monkeypatch.setattr(tavily_search_provider, "TAVILY_SECRET_ARN", "secret-arn")

    assert tavily_search_provider.TavilySearchProvider._load_secret_key() == "secret-value"
