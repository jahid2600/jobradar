from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalize a job URL for duplicate detection."""

    parsed = urlparse(url)

    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip("/"),
        "",
        "",
        "",
    ))


def deduplicate_jobs(jobs):
    """Remove duplicate job URLs while preserving the first occurrence."""

    seen = set()
    unique_jobs = []

    for job in jobs:
        normalized = normalize_url(job.url)

        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        unique_jobs.append(job)

    return unique_jobs
