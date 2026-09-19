import json
import logging

from backend.aws_client import bedrock_runtime
from backend.config import (
    BEDROCK_MODEL_ID,
    SEARCH_STRATEGY_MAX_QUERIES,
    TARGET_LOCATION,
    TARGET_EXPERIENCE,
    TARGET_ROLES,
    TARGET_SKILLS,
)


MODEL_ID = BEDROCK_MODEL_ID
logger = logging.getLogger(__name__)


def deterministic_search_strategy(profile: dict) -> dict:
    """Build a bounded local strategy when Bedrock is unavailable."""

    location = profile["location"]
    experience = profile["experience"]
    roles = profile["target_roles"]
    skills = profile["skills"]
    role_terms = roles[:SEARCH_STRATEGY_MAX_QUERIES]
    queries = [
        f"{role} {location} {experience}"
        for role in role_terms
    ]

    if len(queries) < SEARCH_STRATEGY_MAX_QUERIES:
        queries.extend([
            f"AWS DevOps fresher {location}",
            f"Cloud Operations {location} entry level {skills[0]}",
        ])

    return {
        "primary_titles": roles[:SEARCH_STRATEGY_MAX_QUERIES],
        "alternative_titles": [],
        "keywords": skills,
        "negative_keywords": ["senior", "lead", "architect", "manager"],
        "search_queries": _bounded_queries(queries),
    }


def _bounded_queries(queries: list[str]) -> list[str]:
    unique_queries = []
    seen = set()
    for query in queries:
        normalized = " ".join(str(query).split()).strip()
        if normalized and normalized.lower() not in seen:
            seen.add(normalized.lower())
            unique_queries.append(normalized)
        if len(unique_queries) >= SEARCH_STRATEGY_MAX_QUERIES:
            break
    return unique_queries


def validate_search_strategy(strategy: dict, profile: dict) -> dict:
    """Validate and bound model output before it can drive Tavily."""

    if not isinstance(strategy, dict):
        raise ValueError("Bedrock search strategy must be a JSON object.")

    raw_queries = strategy.get("search_queries")
    if not isinstance(raw_queries, list):
        raise ValueError("Bedrock search strategy must contain search_queries.")

    queries = _bounded_queries(raw_queries)
    location = profile["location"].lower()
    if not queries or any(location not in query.lower() for query in queries):
        raise ValueError("Search strategy queries must include the target location.")

    relevant_terms = [
        *profile["target_roles"],
        *profile["skills"],
        "cloud",
        "devops",
        "infrastructure",
        "sre",
    ]
    if any(
        not any(term.lower() in query.lower() for term in relevant_terms)
        for query in queries
    ):
        raise ValueError("Search strategy contains irrelevant query vocabulary.")

    strategy["search_queries"] = queries
    return strategy


def build_search_prompt(profile: dict | None = None):
    profile = profile or {
        "location": TARGET_LOCATION,
        "experience": TARGET_EXPERIENCE,
        "target_roles": TARGET_ROLES,
        "skills": TARGET_SKILLS,
        "preferred_company_types": [],
    }
    roles = ", ".join(profile["target_roles"])
    skills = ", ".join(profile["skills"])
    company_types = ", ".join(profile.get("preferred_company_types", []))

    return f"""
You are the autonomous job discovery engine for JobRadar.

Candidate requirements:

Location: {profile["location"]}
Experience: {profile["experience"]}
Target roles: {roles}
Skills: {skills}
Preferred company types: {company_types}

Your task is to expand the candidate's search vocabulary.

Generate:

1. Primary job titles
2. Alternative job titles
3. Important search keywords
4. Negative keywords
5. Up to {SEARCH_STRATEGY_MAX_QUERIES} optimized search queries

Rules:
- Include the target location in every search query.
- Focus on the target experience range.
- Focus on AWS Cloud, Cloud Engineering and DevOps.
- Include internships and entry-level opportunities.
- Avoid senior, lead, architect and manager positions.
- Avoid unrelated software-development roles.
- Do not invent companies or job openings.

Return ONLY valid JSON in this exact structure:

{{
  "primary_titles": [],
  "alternative_titles": [],
  "keywords": [],
  "negative_keywords": [],
  "search_queries": []
}}

Do not include markdown, explanations, or code fences.
"""


def generate_search_strategy(profile: dict | None = None, client=bedrock_runtime):
    profile = profile or {
        "location": TARGET_LOCATION,
        "experience": TARGET_EXPERIENCE,
        "target_roles": TARGET_ROLES,
        "skills": TARGET_SKILLS,
    }
    prompt = build_search_prompt(profile)

    response = client.converse(
        modelId=MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        inferenceConfig={
            "maxTokens": 1200,
            "temperature": 0.2,
        },
    )

    result = response["output"]["message"]["content"][0]["text"].strip()
    if result.startswith("```"):
        result = result.replace("```json", "", 1).replace("```", "", 1).strip()

    return validate_search_strategy(json.loads(result), profile)


def get_search_strategy(profile: dict, client=bedrock_runtime) -> dict:
    try:
        strategy = generate_search_strategy(profile, client=client)
        logger.info("Generated search strategy", extra={"query_count": len(strategy["search_queries"])})
        return strategy
    except Exception as exc:
        logger.warning("Bedrock search strategy failed; using fallback", extra={"failure": str(exc)})
        strategy = deterministic_search_strategy(profile)
        logger.info("Using deterministic search strategy", extra={"query_count": len(strategy["search_queries"])})
        return strategy


if __name__ == "__main__":
    print("Running JobRadar search-strategy engine...\n")

    result = generate_search_strategy()

    print("===== JOBRADAR SEARCH STRATEGY =====")
    print(json.dumps(result, indent=2))