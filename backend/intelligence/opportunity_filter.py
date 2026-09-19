from urllib.parse import urlparse

from backend.config import TARGET_LOCATION, TARGET_ROLES


LOCATION_ALIASES = {
    "bengaluru": {"bengaluru", "bangalore"},
}


AGGREGATE_DOMAINS = (
    "indeed.com",
    "naukri.com",
    "simplyhired.co.in",
    "simplyhired.com",
)


AGGREGATE_PATH_HINTS = (
    "/job-search",
    "/q-",
    "/search",
)


AGGREGATE_TITLE_HINTS = (
    "jobs in ",
    "job vacancies",
    "open jobs",
    "jobs today",
    "jobs –",
    "jobs -",
    "job listings",
    "job search",
)


def is_aggregate_page(job) -> bool:
    """Detect obvious search-result or multi-job pages."""

    url = job.url.lower()
    title = job.title.lower().strip()

    parsed = urlparse(url)
    path = parsed.path
    domain = parsed.netloc

    # Known job-search platforms with aggregate URLs.
    if any(domain.endswith(d) for d in AGGREGATE_DOMAINS):
        if any(hint in path for hint in AGGREGATE_PATH_HINTS):
            return True

    # Search-result style titles.
    if any(hint in title for hint in AGGREGATE_TITLE_HINTS):
        return True

    # Very generic multi-job page titles.
    if title.startswith("cloud & devops jobs"):
        return True

    return False


def filter_opportunities(jobs):
    """Remove aggregate pages and clearly out-of-target opportunities."""

    filtered = []
    for job in jobs:
        try:
            if not is_aggregate_page(job) and is_relevant_opportunity(job):
                filtered.append(job)
        except (AttributeError, TypeError) as exc:
            import logging
            logging.getLogger(__name__).warning(
                "Malformed opportunity skipped during filtering",
                extra={"failure": str(exc)},
            )
    return filtered


def is_relevant_opportunity(job) -> bool:
    text = " ".join([
        job.title or "",
        job.description or "",
        job.experience or "",
    ]).lower()
    location = (job.location or "").lower()
    role_match = any(role.lower() in (job.title or "").lower() for role in TARGET_ROLES)
    cloud_match = any(term in text for term in ("aws", "cloud", "devops", "infrastructure", "sre"))
    target_location = TARGET_LOCATION.lower()
    accepted_locations = LOCATION_ALIASES.get(target_location, {target_location})
    location_match = bool(location) and any(
        accepted in location
        for accepted in accepted_locations
    )
    entry_level_match = any(term in text for term in ("0-1", "fresher", "intern", "entry", "graduate"))
    return location_match and (role_match or cloud_match) and entry_level_match
