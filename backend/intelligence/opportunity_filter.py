from urllib.parse import urlparse


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
    """Remove obvious aggregate/search pages."""

    return [
        job
        for job in jobs
        if not is_aggregate_page(job)
    ]
