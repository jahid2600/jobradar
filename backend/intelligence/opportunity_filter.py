from urllib.parse import urlparse


AGGREGATE_DOMAINS = (
    "indeed.com",
    "naukri.com",
)


AGGREGATE_PATH_HINTS = (
    "/job-search",
    "/q-",
)


def is_aggregate_page(job) -> bool:
    """Detect obvious search-result pages."""

    url = job.url.lower()
    path = urlparse(url).path
    domain = urlparse(url).netloc

    # Strong aggregate signals on known job-search platforms.
    if any(domain.endswith(d) for d in AGGREGATE_DOMAINS):
        if any(hint in path for hint in AGGREGATE_PATH_HINTS):
            return True

    return False


def filter_opportunities(jobs):
    """Remove obvious aggregate/search pages."""

    return [
        job
        for job in jobs
        if not is_aggregate_page(job)
    ]
