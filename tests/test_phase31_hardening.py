from botocore.exceptions import ClientError
import importlib

from backend.discovery.job_schema import Job
from backend.intelligence.deduplication import deduplicate_jobs
from backend.intelligence.opportunity_filter import filter_opportunities
from backend.storage.dynamodb_job_store import save_jobs_with_report
from backend.pipeline import run_pipeline


def job(url, description="AWS cloud role for a fresher working with Linux and Terraform.", **kwargs):
    return Job(
        title=kwargs.get("title", "AWS Cloud Engineer"),
        company=kwargs.get("company", "Example Cloud"),
        location=kwargs.get("location", "Bengaluru"),
        url=url,
        source=kwargs.get("source", "tavily"),
        description=description,
        experience="0-1 years",
        posted_date=kwargs.get("posted_date"),
    )


def conditional_failure():
    return ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "exists"}},
        "PutItem",
    )


def test_same_job_across_sources_deduplicates_by_content():
    first = job("https://company.example/jobs/1", source="company")
    second = job("https://linkedin.example/jobs/other", source="linkedin")

    assert len(deduplicate_jobs([first, second])) == 1


def test_distinct_requisitions_with_same_visible_metadata_are_preserved():
    first = job("https://company.example/jobs/1", description="First requisition: AWS cloud role for a fresher working with Linux and Terraform.")
    second = job("https://company.example/jobs/2", description="Second requisition: AWS cloud role for a fresher working with Docker and CI/CD.")

    assert len(deduplicate_jobs([first, second])) == 2


def test_missing_company_or_location_does_not_create_composite_collision():
    first = job("https://one.example/jobs/1", company="", location="")
    second = job("https://two.example/jobs/2", company="", location="")

    assert len(deduplicate_jobs([first, second])) == 2


def test_identical_url_deduplicates_even_with_changed_metadata():
    first = job("https://company.example/jobs/1", description="First metadata description for this AWS cloud fresher role.")
    second = job("https://company.example/jobs/1", title="Different title", description="Different metadata description for this role.")

    assert len(deduplicate_jobs([first, second])) == 1


def test_unknown_location_is_rejected():
    unknown = job("https://company.example/jobs/1", location="")

    assert filter_opportunities([unknown]) == []


class ConditionalDynamoClient:
    def __init__(self):
        self.writes = 0

    def put_item(self, **kwargs):
        self.writes += 1
        if self.writes > 1:
            raise conditional_failure()


def test_conditional_duplicate_is_existing_not_failure():
    result = {
        "job": job("https://company.example/jobs/1"),
        "qualification": {
            "qualified": True,
            "relevance_score": 90,
            "reason": "Strong match",
        },
    }
    report = save_jobs_with_report([result, result], client=ConditionalDynamoClient())

    assert len(report.saved) == 1
    assert report.existing == 1
    assert report.failures == 0


def test_idle_status_does_not_infer_metrics_from_local_json(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "jobs.json").write_text(
        '[{"qualification": {"qualified": true}}]',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    api = importlib.reload(importlib.import_module("api"))
    status = api.latest_run

    assert status["status"] == "idle"
    assert status["raw_discovered"] == 0
    assert status["filtered"] == 0
    assert status["unique"] == 0
    assert status["new_opportunities"] == 0
    assert status["persisted_new"] == 0


class CountingProvider:
    def __init__(self, results=None):
        self.queries = []
        self.results = results or [job("https://company.example/jobs/1")]

    def search(self, query):
        self.queries.append(query)
        return self.results


class AlwaysQualified:
    def evaluate(self, opportunity, profile):
        return {
            "qualified": True,
            "relevance_score": 90,
            "reason": "match",
            "matched_requirements": [],
            "skill_gaps": [],
            "concerns": [],
        }


class EmptyExisting:
    def existing_identities(self):
        return set()


def run_with(provider, strategy, query=None, save=None):
    return run_pipeline(
        query,
        provider_factory=lambda: provider,
        strategy_factory=lambda profile: {"search_queries": strategy},
        qualification_engine=AlwaysQualified(),
        opportunity_service=EmptyExisting(),
        save_dynamodb=save or (lambda results: results),
        save_local=lambda results: None,
        return_details=True,
    )


def test_query_cap_cannot_be_bypassed_by_explicit_query():
    provider = CountingProvider()
    run = run_with(provider, [f"AWS Cloud Engineer Bengaluru {index}" for index in range(20)], query="manual query")

    assert len(provider.queries) == 8
    assert run.metrics["raw_discovered"] == 8


def test_total_discovery_results_are_hard_capped():
    provider = CountingProvider([
        job(
            f"https://company.example/jobs/{index}",
            description=f"Unique AWS cloud fresher opportunity number {index} with Linux and Terraform.",
        )
        for index in range(100)
    ])
    run = run_with(provider, ["AWS Cloud Engineer Bengaluru"])

    assert run.metrics["raw_discovered"] == 50


def test_failed_persistence_does_not_count_as_new_opportunity():
    run = run_with(CountingProvider(), ["AWS Cloud Engineer Bengaluru"], save=lambda results: [])

    assert run.metrics["new_candidates"] == 1
    assert run.metrics["persisted_new"] == 0
    assert run.metrics["new_opportunities"] == 0
    assert run.metrics["persistence_failures"] == 1


def test_provider_initialization_failure_is_reported():
    run = run_pipeline(
        provider_factory=lambda: (_ for _ in ()).throw(RuntimeError("provider unavailable")),
        strategy_factory=lambda profile: {"search_queries": ["AWS Cloud Engineer Bengaluru"]},
        opportunity_service=EmptyExisting(),
        save_dynamodb=lambda results: results,
        save_local=lambda results: None,
        return_details=True,
    )

    assert any("provider initialization" in failure for failure in run.failures)