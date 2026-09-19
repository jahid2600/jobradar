from dataclasses import dataclass

from backend.config import (
    TARGET_LOCATION,
    TARGET_ROLES,
    TARGET_SKILLS,
)
from backend.discovery.job_schema import Job


@dataclass
class QualificationResult:
    job: Job
    qualified: bool
    score: int
    reasons: list[str]
    missing_skills: list[str]


class QualificationEngine:
    """Evaluate whether a discovered job matches the user's target profile."""

    def evaluate(self, job: Job) -> QualificationResult:
        score = 0
        reasons = []
        missing_skills = []

        job_text = " ".join(
            [
                job.title or "",
                job.description or "",
                job.experience or "",
            ]
        ).lower()

        # Location
        location_match = TARGET_LOCATION.lower() in (
            job.location or ""
        ).lower()

        if location_match:
            score += 25
            reasons.append("Location matches Bengaluru.")
        else:
            reasons.append("Location does not match Bengaluru.")

        # Role
        role_match = any(
            role.lower() in (job.title or "").lower()
            for role in TARGET_ROLES
        )

        if role_match:
            score += 30
            reasons.append("Job title matches a target role.")
        else:
            reasons.append("Job title does not match a target role.")

        # Experience
        experience_text = (job.experience or "").lower()

        entry_level_match = (
            "0-1" in experience_text
            or "fresher" in experience_text
            or "intern" in experience_text
            or "entry" in experience_text
        )

        if entry_level_match:
            score += 20
            reasons.append(
                "Experience level is suitable for an entry-level candidate."
            )
        else:
            reasons.append(
                "Experience requirement may not fit the target profile."
            )

        # Cloud / AWS / DevOps relevance
        cloud_keywords = [
            "aws",
            "cloud",
            "devops",
            "infrastructure",
            "site reliability",
            "sre",
        ]

        cloud_relevance = any(
            keyword in job_text
            for keyword in cloud_keywords
        )

        if cloud_relevance:
            score += 15
            reasons.append("Job is relevant to Cloud/AWS/DevOps.")
        else:
            reasons.append(
                "Job does not show clear Cloud/AWS/DevOps relevance."
            )

        # Skills
        matched_skills = []

        for skill in TARGET_SKILLS:
            if skill.lower() in job_text:
                matched_skills.append(skill)
            else:
                missing_skills.append(skill)

        if matched_skills:
            skill_points = min(10, len(matched_skills) * 2)
            score += skill_points
            reasons.append(
                f"Matched skills: {', '.join(matched_skills)}."
            )

        # Qualification gates
        qualified = (
            location_match
            and entry_level_match
            and cloud_relevance
            and score >= 60
        )

        return QualificationResult(
            job=job,
            qualified=qualified,
            score=score,
            reasons=reasons,
            missing_skills=missing_skills,
        )