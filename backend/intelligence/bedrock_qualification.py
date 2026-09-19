import json

from backend.aws_client import bedrock_runtime


MODEL_ID = "deepseek.v3.2"


class BedrockQualificationEngine:
    """Use Amazon Bedrock to semantically evaluate a job."""

    def evaluate(self, job, profile):
        prompt = f"""
You are the semantic qualification engine for JobRadar.

Evaluate whether this job is relevant to the candidate's target profile.

CANDIDATE PROFILE:
{json.dumps(profile, indent=2)}

JOB:
{json.dumps(job.to_dict(), indent=2)}

Return ONLY valid JSON in exactly this structure:

{{
  "qualified": true,
  "relevance_score": 0,
  "reason": "Short explanation",
  "matched_requirements": [],
  "skill_gaps": [],
  "concerns": []
}}

Rules:
- relevance_score must be an integer from 0 to 100.
- Consider role relevance, AWS/Cloud/DevOps relevance,
  location, experience level, and skills.
- Do not invent requirements that are not present in the job.
- Be conservative when information is missing.
- qualified should be true only when the job is reasonably suitable
  for this candidate.
"""

        response = bedrock_runtime.converse(
            modelId=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ],
                }
            ],
        )

        text = response["output"]["message"]["content"][0]["text"].strip()

        if text.startswith("```"):
            text = text.replace("```json", "", 1)
            text = text.replace("```", "", 1)
            text = text.strip()

        return json.loads(text)