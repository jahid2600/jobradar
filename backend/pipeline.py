from backend.discovery.tavily_search_provider import TavilySearchProvider
from backend.intelligence.bedrock_qualification import BedrockQualificationEngine
from backend.intelligence.candidate_profile import get_candidate_profile
from backend.intelligence.opportunity_filter import filter_opportunities
from backend.intelligence.deduplication import deduplicate_jobs
from backend.storage.dynamodb_job_store import save_jobs as save_dynamodb_jobs
from backend.storage.job_store import save_jobs as save_local_jobs


def run_pipeline(query: str):
    print(f"\nSearching the web for: {query}\n")

    provider = TavilySearchProvider()
    jobs = provider.search(query)

    print(f"Discovered jobs: {len(jobs)}")

    jobs = filter_opportunities(jobs)
    print(f"Individual opportunities after filtering: {len(jobs)}")

    jobs = deduplicate_jobs(jobs)
    print(f"Unique opportunities after deduplication: {len(jobs)}")

    profile = get_candidate_profile()
    engine = BedrockQualificationEngine()

    results = []

    for index, job in enumerate(jobs, start=1):
        print(f"\n[{index}/{len(jobs)}] {job.title}")
        print(f"URL: {job.url}")

        qualification = engine.evaluate(job, profile)

        result = {
            "job": job,
            "qualification": qualification,
        }

        results.append(result)

        print(f"Qualified: {qualification['qualified']}")
        print(f"Score: {qualification['relevance_score']}")
        print(f"Reason: {qualification['reason']}")

    qualified_count = sum(
        1 for result in results
        if result["qualification"]["qualified"]
    )

    print("\n===== JOBRADAR SUMMARY =====")
    print(f"Jobs discovered: {len(results)}")
    print(f"Qualified opportunities: {qualified_count}")

    save_local_jobs(results)
    save_dynamodb_jobs(results)
    print("Results saved to data/jobs.json and DynamoDB")

    return results


if __name__ == "__main__":
    run_pipeline("AWS Cloud Engineer Bengaluru fresher")
