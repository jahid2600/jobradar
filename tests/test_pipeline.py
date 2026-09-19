from backend.discovery.job_schema import Job
from backend.intelligence.deduplication import job_identity_keys
from backend.pipeline import run_pipeline


def make_job(title, company, url):
    return Job(
        title=title,
        company=company,
        location="Bengaluru",
        url=url,
        source="tavily",
        description="AWS cloud role for fresher with Linux and Terraform.",
        experience="0-1 years",
    )


class FakeProvider:
    def search(self, query):
        return [
            make_job("AWS Cloud Engineer", "Example Cloud", f"https://{query}.example/1"),
            make_job("AWS Cloud Engineer", "Example Cloud", f"https://other-{query}.example/1"),
            make_job("Junior DevOps Engineer", "Another Systems", f"https://{query}.example/2"),
            object(),
        ]


class FakeQualificationEngine:
    def evaluate(self, job, profile):
        return {
            "qualified": True,
            "relevance_score": 80,
            "reason": "Matches target",
            "matched_requirements": ["AWS"],
            "skill_gaps": [],
            "concerns": [],
        }


class FakeOpportunityService:
    def existing_identities(self):
        return job_identity_keys(make_job(
            "Junior DevOps Engineer",
            "Another Systems",
            "https://existing.example/2",
        ))


def test_pipeline_calculates_metrics_and_only_saves_new_qualified_jobs():
    saved_to_dynamodb = []
    saved_locally = []

    run = run_pipeline(
        provider_factory=FakeProvider,
        strategy_factory=lambda profile: {"search_queries": ["q1", "q2"]},
        qualification_engine=FakeQualificationEngine(),
        opportunity_service=FakeOpportunityService(),
        save_dynamodb=lambda results: saved_to_dynamodb.extend(results) or results,
        save_local=lambda results: saved_locally.extend(results),
        return_details=True,
    )

    assert run.metrics["raw_discovered"] == 8
    assert run.metrics["filtered"] == 6
    assert run.metrics["unique"] == 2
    assert run.metrics["duplicates"] == 4
    assert run.metrics["qualified"] == 2
    assert run.metrics["new_opportunities"] == 1
    assert len(saved_to_dynamodb) == 1
    assert len(saved_locally) == 1


def test_pipeline_falls_back_when_strategy_factory_fails():
    run = run_pipeline(
        provider_factory=lambda: FakeProvider(),
        strategy_factory=lambda profile: (_ for _ in ()).throw(RuntimeError("model down")),
        qualification_engine=FakeQualificationEngine(),
        opportunity_service=FakeOpportunityService(),
        save_dynamodb=lambda results: results,
        save_local=lambda results: None,
        return_details=True,
    )

    assert run.metrics["raw_discovered"] > 0
    assert any("search strategy" in failure for failure in run.failures)


def test_pipeline_reports_real_stage_transitions():
    stages = []
    run_pipeline(
        provider_factory=FakeProvider,
        strategy_factory=lambda profile: {"search_queries": ["q1"]},
        qualification_engine=FakeQualificationEngine(),
        opportunity_service=FakeOpportunityService(),
        save_dynamodb=lambda results: results,
        save_local=lambda results: None,
        progress_callback=lambda stage, progress, metrics, failures: stages.append((stage, progress, metrics)),
        return_details=True,
    )

    assert [stage for stage, _, _ in stages] == [
        "generating_strategy",
        "searching",
        "searching",
        "normalizing",
        "filtering",
        "deduplicating",
        "qualifying",
        "qualifying",
        "qualifying",
        "persisting",
        "persisting",
        "completed",
    ]
    assert stages[3][2]["raw_discovered"] == 4