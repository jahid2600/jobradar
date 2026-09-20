import logging
from datetime import datetime, timezone
from typing import Any

from backend.aws_client import cloudwatch
from backend.config import CLOUDWATCH_METRICS_ENABLED, CLOUDWATCH_METRICS_NAMESPACE


logger = logging.getLogger(__name__)


def publish_run_metrics(
    metrics: dict[str, int],
    *,
    success: bool,
    notification_failure: bool,
    client: Any = cloudwatch,
    enabled: bool = CLOUDWATCH_METRICS_ENABLED,
) -> None:
    """Publish low-cardinality radar metrics when CloudWatch is enabled."""

    if not enabled:
        return

    metric_values = [
        {"MetricName": "RadarRunSuccess", "Value": 1 if success else 0, "Unit": "Count"},
        {"MetricName": "RadarRunFailure", "Value": 0 if success else 1, "Unit": "Count"},
        {"MetricName": "RawDiscovered", "Value": metrics.get("raw_discovered", 0), "Unit": "Count"},
        {"MetricName": "Qualified", "Value": metrics.get("qualified", 0), "Unit": "Count"},
        {"MetricName": "PersistedNew", "Value": metrics.get("persisted_new", 0), "Unit": "Count"},
        {"MetricName": "NotificationFailure", "Value": 1 if notification_failure else 0, "Unit": "Count"},
    ]
    try:
        client.put_metric_data(
            Namespace=CLOUDWATCH_METRICS_NAMESPACE,
            MetricData=[{
                **metric,
                "Timestamp": datetime.now(timezone.utc),
            } for metric in metric_values],
        )
    except Exception:
        logger.exception("CloudWatch metric publication failed")
