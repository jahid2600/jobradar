import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


TRACKING_QUERY_KEYS = {"ref", "source", "trk", "trkcampaign"}
REQUISITION_QUERY_KEYS = {
    "gh_jid",
    "job_id",
    "jobid",
    "jk",
    "req",
    "reqid",
    "requisition",
    "requisitionid",
}


def normalize_url(url: str) -> str:
    """Canonicalize a URL while preserving meaningful job identifiers."""

    parsed = urlparse(url or "")
    query = [
        (key.lower(), value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in TRACKING_QUERY_KEYS
    ]

    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip("/"),
        "",
        urlencode(sorted(query)),
        "",
    ))


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _field(job, name: str):
    if isinstance(job, dict):
        return job.get(name)
    return getattr(job, name, None)


def _requisition_key(url: str) -> str | None:
    parsed = urlparse(url or "")
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in REQUISITION_QUERY_KEYS and value.strip():
            return f"req:{parsed.netloc.lower()}:{_normalize_text(value)}"
    return None


def _description_fingerprint(description: str) -> str | None:
    normalized = _normalize_text(description)
    if len(normalized) < 40:
        return None
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]
    return f"description:{digest}"


def job_identity_keys(job) -> set[str]:
    """Return conservative keys that may identify one opportunity."""

    keys = set()
    url = normalize_url(_field(job, "url"))
    if url:
        keys.add(f"url:{url}")

    requisition = _requisition_key(_field(job, "url"))
    if requisition:
        keys.add(requisition)

    title = _normalize_text(_field(job, "title"))
    company = _normalize_text(_field(job, "company"))
    location = _normalize_text(_field(job, "location"))
    description_key = _description_fingerprint(_field(job, "description"))
    posted_date = _normalize_text(_field(job, "posted_date"))

    # Without all three stable fields, a composite key would make missing
    # metadata increase collisions. URL/requisition keys remain available.
    if title and company and location:
        signal = description_key or (f"posted:{posted_date}" if posted_date else None)
        if signal:
            keys.add(f"composite:{title}|{company}|{location}|{signal}")

    return keys


def job_identity(job) -> str:
    """Return a deterministic primary identity key for storage/lookups."""

    keys = job_identity_keys(job)
    urls = sorted(key for key in keys if key.startswith("url:"))
    if urls:
        return urls[0]
    requisition = sorted(key for key in keys if key.startswith("req:"))
    if requisition:
        return requisition[0]
    composite = sorted(key for key in keys if key.startswith("composite:"))
    return composite[0] if composite else ""


def deduplicate_jobs(jobs):
    """Deduplicate only when a strong or content-backed identity matches."""

    seen = set()
    unique_jobs = []

    for job in jobs:
        keys = job_identity_keys(job)
        if keys and keys & seen:
            continue
        seen.update(keys)
        unique_jobs.append(job)

    return unique_jobs
