from backend.discovery.job_schema import Job
from backend.intelligence.bedrock_qualification import (
    BedrockQualificationEngine,
)
from backend.intelligence.candidate_profile import get_candidate_profile


def test_bedrock_qualification(monkeypatch):
    job = Job(
        title="Junior AWS Cloud Engineer",
        company="Test Cloud",
        location="Bengaluru",
        url="https://example.com/job",
        source="test",
        description=(
            "Entry-level AWS Cloud Engineer role. "
            "Work with AWS, Linux, Python, Docker and Terraform."
        ),
        experience="0-1 years",
    )

    profile = get_candidate_profile()

    class FakeBedrockRuntime:
        def converse(self, **kwargs):
            return {
                "output": {
                    "message": {
                        "content": [{
                            "text": (
                                '{"qualified": true, "relevance_score": 90, '
                                '"reason": "Strong match", '
                                '"matched_requirements": ["AWS"], '
                                '"skill_gaps": [], "concerns": []}'
                            )
                        }]
                    }
                }
            }

    monkeypatch.setattr(
        "backend.intelligence.bedrock_qualification.bedrock_runtime",
        FakeBedrockRuntime(),
    )

    engine = BedrockQualificationEngine()
    result = engine.evaluate(job, profile)

    print("\nBedrock result:")
    print(result)

    assert isinstance(result, dict)
    assert "qualified" in result
    assert "relevance_score" in result
    assert "reason" in result
    assert "matched_requirements" in result
    assert "skill_gaps" in result
    assert "concerns" in result