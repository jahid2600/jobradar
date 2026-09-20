import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from backend.config import (
    HARD_MAX_DISCOVERY_RESULTS,
    HARD_MAX_QUALIFICATION_CANDIDATES,
    SNS_ENABLED,
    SEARCH_STRATEGY_MAX_QUERIES,
    SQS_ASYNC_PROCESSING,
    SQS_ENABLED,
)
from backend.discovery.job_search import deterministic_search_strategy, get_search_strategy
from backend.discovery.tavily_search_provider import TavilySearchProvider
from backend.intelligence.bedrock_qualification import BedrockQualificationEngine
from backend.intelligence.candidate_profile import get_candidate_profile
from backend.intelligence.deduplication import job_identity_keys
from backend.intelligence.opportunity_filter import filter_opportunities
from backend.notifications import notify_new_opportunities
from backend.observability import publish_run_metrics
from backend.queueing import enqueue_discovery_jobs
from backend.services.opportunity_service import DynamoDBOpportunityService
from backend.storage.dynamodb_job_store import save_jobs_with_report
from backend.storage.job_store import save_jobs as save_local_jobs
from backend.storage.raw_discovery_store import store_raw_discovery


logger = logging.getLogger(__name__)


@dataclass
class PipelineRun:
    results: list[dict[str, Any]]
    metrics: dict[str, int]
    failures: list[str] = field(default_factory=list)
    generated_query_count: int = 0
    run_id: str | None = None
    notification: dict[str, Any] = field(default_factory=dict)



def _empty_metrics() -> dict[str, int]:
    return {
        "raw_discovered": 0,
        "filtered": 0,
        "unique": 0,
        "qualified": 0,
        "new_opportunities": 0,
        "duplicates": 0,
        "new_candidates": 0,
        "persisted_new": 0,
        "existing": 0,
        "persistence_failures": 0,
        "queued": 0,
        "queue_failures": 0,
    }


def _job_keys(job) -> set[str]:
    return job_identity_keys(job)


def run_pipeline(
    query: str | None = None,
    *,
    provider_factory: Callable[[], Any] = TavilySearchProvider,
    strategy_factory: Callable[[dict], dict] = get_search_strategy,
    qualification_engine: Any | None = None,
    opportunity_service: Any | None = None,
    save_dynamodb: Callable[[list[dict[str, Any]]], Any] = save_jobs_with_report,
    save_local: Callable[[list[dict[str, Any]]], None] = save_local_jobs,
    return_details: bool = False,
    run_id: str | None = None,
    progress_callback: Callable[[str, int | None, dict[str, int], list[str]], None] | None = None,
    notification_func: Callable[[list[dict[str, Any]], str | None], dict[str, Any]] = notify_new_opportunities,
) -> list[dict[str, Any]] | PipelineRun:
    """Run autonomous discovery and preserve the historic list return by default."""

    started_at = time.monotonic()
    profile = get_candidate_profile()
    failures = []
    metrics = _empty_metrics()
    notification = {
        "attempted": False,
        "enabled": SNS_ENABLED,
        "published": False,
        "error": None,
    }

    def emit(stage: str, progress: int | None = None) -> None:
        if progress_callback is None:
            return
        try:
            progress_callback(stage, progress, dict(metrics), list(failures))
        except Exception:
            logger.exception("Pipeline progress callback failed", extra={"run_id": run_id})

    logger.info("Radar pipeline started", extra={"run_id": run_id})
    emit("generating_strategy")

    try:
        strategy = strategy_factory(profile)
    except Exception as exc:
        logger.exception("Search strategy generation failed", extra={"run_id": run_id})
        failures.append(f"search strategy: {exc}")
        strategy = deterministic_search_strategy(profile)

    if not strategy.get("search_queries"):
        logger.warning("Search strategy was empty; using deterministic fallback", extra={"run_id": run_id})
        failures.append("search strategy returned no queries")
        strategy = deterministic_search_strategy(profile)

    queries = [str(item).strip() for item in strategy.get("search_queries", []) if str(item).strip()]
    if query and query not in queries:
        queries = [query, *queries]
    queries = queries[:SEARCH_STRATEGY_MAX_QUERIES]

    logger.info("Search strategy ready", extra={"run_id": run_id, "query_count": len(queries)})
    emit("searching", 0)
    discovered_jobs = []
    raw_payloads = []

    try:
        provider = provider_factory()
    except Exception as exc:
        logger.exception("Search provider initialization failed", extra={"run_id": run_id})
        failures.append(f"search provider initialization: {exc}")
        provider = None

    if provider is not None:
        for query_index, search_query in enumerate(queries, start=1):
            if len(discovered_jobs) >= HARD_MAX_DISCOVERY_RESULTS:
                failures.append("discovery result cap reached")
                break
            logger.info("Searching query", extra={"run_id": run_id, "query": search_query})
            try:
                if hasattr(provider, "search_with_raw"):
                    raw_items, query_jobs = provider.search_with_raw(search_query)
                    raw_payloads.extend(raw_items if isinstance(raw_items, list) else [])
                else:
                    query_jobs = provider.search(search_query)
                if not isinstance(query_jobs, list):
                    raise ValueError("search provider did not return a list")
                remaining = HARD_MAX_DISCOVERY_RESULTS - len(discovered_jobs)
                accepted_jobs = [job for job in query_jobs if job is not None][:remaining]
                metrics_raw_count = len(accepted_jobs)
                for job in accepted_jobs:
                    try:
                        job_identity_keys(job)
                        discovered_jobs.append(job)
                    except (AttributeError, TypeError, ValueError) as malformed_exc:
                        failures.append(f"malformed result: {malformed_exc}")
                        logger.warning("Malformed normalized opportunity skipped", extra={"run_id": run_id, "failure": str(malformed_exc)})
                logger.info("Search query completed", extra={"run_id": run_id, "query": search_query, "count": metrics_raw_count})
                failures.extend(getattr(provider, "last_failures", []))
            except Exception as exc:
                logger.exception("Search query failed", extra={"run_id": run_id, "query": search_query})
                failures.append(f"search query '{search_query}': {exc}")
            emit("searching", round(query_index / len(queries) * 100) if queries else None)

    metrics["raw_discovered"] = len(discovered_jobs)
    raw_storage = store_raw_discovery(run_id or "unassigned", raw_payloads or discovered_jobs)
    if raw_storage["failures"]:
        failures.append(f"{raw_storage['failures']} raw S3 writes failed")
    logger.info("Raw discovery complete", extra={"run_id": run_id, "raw_discovered": metrics["raw_discovered"]})
    emit("normalizing")

    try:
        filtered_jobs = filter_opportunities(discovered_jobs)
    except Exception as exc:
        logger.exception("Opportunity filtering failed", extra={"run_id": run_id})
        failures.append(f"filtering: {exc}")
        filtered_jobs = []

    metrics["filtered"] = len(filtered_jobs)
    emit("filtering")
    unique_jobs = []
    seen_keys = set()
    for job in filtered_jobs:
        try:
            keys = _job_keys(job)
        except (AttributeError, TypeError) as exc:
            logger.warning("Malformed opportunity skipped", extra={"run_id": run_id, "failure": str(exc)})
            failures.append(f"malformed result: {exc}")
            continue
        if keys & seen_keys:
            metrics["duplicates"] += 1
            continue
        seen_keys.update(keys)
        unique_jobs.append(job)

    metrics["unique"] = len(unique_jobs)
    logger.info("Filtering and deduplication complete", extra={"run_id": run_id, "filtered": metrics["filtered"], "unique": metrics["unique"], "duplicates": metrics["duplicates"]})
    emit("deduplicating")

    queue_result = enqueue_discovery_jobs(unique_jobs, run_id, profile)
    metrics["queued"] = queue_result["enqueued"]
    metrics["queue_failures"] = queue_result["failures"]
    if queue_result["failures"]:
        failures.append(f"{queue_result['failures']} SQS enqueue operations failed")

    if SQS_ENABLED and SQS_ASYNC_PROCESSING:
        metrics["duration_ms"] = round((time.monotonic() - started_at) * 1000)
        metrics["new_opportunities"] = 0
        publish_run_metrics(metrics, success=not failures, notification_failure=False)
        emit("completed", 100)
        run = PipelineRun(
            results=[],
            metrics=metrics,
            failures=failures,
            generated_query_count=len(queries),
            run_id=run_id,
            notification=notification,
        )
        return run if return_details else []

    engine = qualification_engine or BedrockQualificationEngine()
    if len(unique_jobs) > HARD_MAX_QUALIFICATION_CANDIDATES:
        failures.append("qualification candidate cap reached")
        unique_jobs = unique_jobs[:HARD_MAX_QUALIFICATION_CANDIDATES]
        metrics["unique"] = len(unique_jobs)
    results = []
    emit("qualifying", 0)
    for index, job in enumerate(unique_jobs, start=1):
        try:
            qualification = engine.evaluate(job, profile)
            results.append({"job": job, "qualification": qualification})
            if qualification.get("qualified", False):
                metrics["qualified"] += 1
            logger.info("Opportunity qualified", extra={"run_id": run_id, "index": index, "qualified": qualification.get("qualified", False)})
        except Exception as exc:
            logger.exception("Opportunity qualification failed", extra={"run_id": run_id, "index": index})
            failures.append(f"qualification for '{getattr(job, 'title', 'unknown')}': {exc}")
        emit("qualifying", round(index / len(unique_jobs) * 100) if unique_jobs else 100)

    qualified_results = [
        result for result in results
        if result["qualification"].get("qualified", False)
    ]

    existing_keys = set()
    existing_lookup_failed = False
    service = opportunity_service or DynamoDBOpportunityService()
    try:
        existing_keys = service.existing_identities()
    except Exception as exc:
        logger.exception("Existing opportunity lookup failed", extra={"run_id": run_id})
        failures.append(f"existing opportunity lookup: {exc}")
        existing_lookup_failed = True

    new_results = []
    if not existing_lookup_failed:
        for result in qualified_results:
            if _job_keys(result["job"]) & existing_keys:
                metrics["existing"] += 1
                continue
            new_results.append(result)

    metrics["new_candidates"] = len(new_results)
    logger.info("Existing opportunity comparison complete", extra={"run_id": run_id, "existing": metrics["existing"], "new_candidates": metrics["new_candidates"]})
    emit("persisting", 0)

    try:
        save_local(new_results)
    except Exception as exc:
        logger.exception("Local opportunity persistence failed", extra={"run_id": run_id})
        failures.append(f"local persistence: {exc}")

    if not existing_lookup_failed:
        persisted_results = []
        try:
            persistence = save_dynamodb(new_results)
            if hasattr(persistence, "saved"):
                persisted_results = persistence.saved
                metrics["persisted_new"] = len(persisted_results)
                metrics["existing"] += persistence.existing
                metrics["persistence_failures"] = persistence.failures
            else:
                persisted_results = persistence or []
                metrics["persisted_new"] = len(persisted_results)
                metrics["persistence_failures"] = len(new_results) - metrics["persisted_new"]
            if metrics["persistence_failures"]:
                failures.append(f"{metrics['persistence_failures']} DynamoDB writes failed")
        except Exception as exc:
            logger.exception("DynamoDB persistence failed", extra={"run_id": run_id})
            failures.append(f"DynamoDB persistence: {exc}")

    if metrics["persisted_new"]:
        try:
            notification = notification_func(persisted_results, run_id)
        except Exception as exc:
            # Notification delivery must never change a successful radar run.
            notification = {
                "attempted": True,
                "enabled": True,
                "published": False,
                "error": str(exc),
            }
            logger.exception("Notification integration failed", extra={"run_id": run_id})

    metrics["duration_ms"] = round((time.monotonic() - started_at) * 1000)
    metrics["new_opportunities"] = metrics["persisted_new"]
    emit("persisting", 100)
    logger.info("Radar pipeline complete", extra={"run_id": run_id, "metrics": metrics, "failure_count": len(failures)})
    publish_run_metrics(
        metrics,
        success=not failures,
        notification_failure=bool(notification.get("error")),
    )
    emit("completed", 100)
    run = PipelineRun(
        results=results,
        metrics=metrics,
        failures=failures,
        generated_query_count=len(queries),
        run_id=run_id,
        notification=notification,
    )
    return run if return_details else results


if __name__ == "__main__":
    run_pipeline()
