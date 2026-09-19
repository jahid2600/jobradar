from backend.config import (
    TARGET_LOCATION,
    TARGET_EXPERIENCE,
    TARGET_ROLES,
    TARGET_SKILLS,
    PREFERRED_COMPANY_TYPES,
)


def get_candidate_profile() -> dict:
    """Return the candidate profile used by JobRadar intelligence."""

    return {
        "location": TARGET_LOCATION,
        "experience": TARGET_EXPERIENCE,
        "target_roles": TARGET_ROLES,
        "skills": TARGET_SKILLS,
        "preferred_company_types": PREFERRED_COMPANY_TYPES,
    }