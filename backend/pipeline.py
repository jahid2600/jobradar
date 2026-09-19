from backend.discovery.mock_search_provider import MockSearchProvider
from backend.intelligence.bedrock_qualification import (
    BedrockQualificationEngine,
)
from backend.intelligence.candidate_profile import get_candidate_profile


def run_pipeline(query: str):
    """Run the JobRadar discovery and qualification pipeline."""

    print(f"\nSearching for: {query}\n")

    # 1. Discover jobs
    provider = MockSearchProvider()
    jobs = provider.search(query)

    print(f"Discovered jobs: {len(jobs)}")

    # 2. Load candidate profile
    profile = get_candidate_profile()

    # 3. Qualify jobs with Bedrock
    engine = BedrockQualificationEngine()

    results = []

    for job in jobs:
        print(f"\nAnalyzing: {job.title} at {job.company}")

        result = engine.evaluate(job, profile)

        results.append(
            {
                "job": job,
                "qualification": result,
            }
        )

        print(f"Qualified: {result['qualified']}")
        print(f"Score: {result['relevance_score']}")
        print(f"Reason: {result['reason']}")

    return results


if __name__ == "__main__":
    run_pipeline("AWS Cloud Engineer Bengaluru fresher")