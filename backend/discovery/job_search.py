import json
from backend.aws_client import bedrock_runtime
from backend.config import (
    TARGET_LOCATION,
    TARGET_EXPERIENCE,
    TARGET_ROLES,
    TARGET_SKILLS,
)


MODEL_ID = "deepseek.v3.2"


def build_search_prompt():
    roles = ", ".join(TARGET_ROLES)
    skills = ", ".join(TARGET_SKILLS)

    return f"""
You are the autonomous job discovery engine for JobRadar.

Candidate requirements:

Location: {TARGET_LOCATION}
Experience: {TARGET_EXPERIENCE}
Target roles: {roles}
Skills: {skills}

Your task is to expand the candidate's search vocabulary.

Generate:

1. Primary job titles
2. Alternative job titles
3. Important search keywords
4. Negative keywords
5. Three optimized search queries

Rules:
- Focus on Bengaluru.
- Focus on 0-1 years experience.
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


def generate_search_strategy():
    prompt = build_search_prompt()

    response = bedrock_runtime.converse(
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

    result = response["output"]["message"]["content"][0]["text"]

    return json.loads(result)


if __name__ == "__main__":
    print("Running JobRadar search-strategy engine...\n")

    result = generate_search_strategy()

    print("===== JOBRADAR SEARCH STRATEGY =====")
    print(json.dumps(result, indent=2))