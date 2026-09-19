import json

from backend.discovery.job_search import (
    deterministic_search_strategy,
    generate_search_strategy,
    get_search_strategy,
)


PROFILE = {
    "location": "Bengaluru",
    "experience": "0-1 years",
    "target_roles": ["AWS Cloud Engineer", "Junior DevOps Engineer"],
    "skills": ["AWS", "Linux", "Terraform"],
}


class FakeStrategyClient:
    def __init__(self, text):
        self.text = text

    def converse(self, **kwargs):
        return {"output": {"message": {"content": [{"text": self.text}]}}}


def test_strategy_json_is_bounded_and_validated():
    queries = [f"AWS Cloud Engineer Bengaluru option {index}" for index in range(20)]
    text = json.dumps({
        "primary_titles": [],
        "alternative_titles": [],
        "keywords": ["AWS"],
        "negative_keywords": [],
        "search_queries": queries,
    })

    strategy = generate_search_strategy(PROFILE, client=FakeStrategyClient(text))

    assert len(strategy["search_queries"]) == 8
    assert all("bengaluru" in query.lower() for query in strategy["search_queries"])


def test_strategy_failure_uses_deterministic_fallback():
    class BrokenClient:
        def converse(self, **kwargs):
            raise RuntimeError("Bedrock unavailable")

    strategy = get_search_strategy(PROFILE, client=BrokenClient())
    fallback = deterministic_search_strategy(PROFILE)

    assert strategy["search_queries"] == fallback["search_queries"]
    assert 1 <= len(strategy["search_queries"]) <= 8