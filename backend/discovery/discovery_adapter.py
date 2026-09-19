from abc import ABC, abstractmethod
from typing import Any

from backend.discovery.job_schema import Job


class DiscoveryAdapter(ABC):
    """Common interface for every JobRadar discovery source."""

    @abstractmethod
    def search(self, query: str) -> list[Job]:
        """Search for jobs using a query."""
        raise NotImplementedError


class RawResultAdapter(DiscoveryAdapter):
    """Convert provider-specific results into JobRadar Job objects."""

    def normalize(self, result: dict[str, Any]) -> Job:
        return Job(
            title=result.get("title", "Unknown"),
            company=result.get("company", "Unknown"),
            location=result.get("location", "Unknown"),
            url=result.get("url", ""),
            source=result.get("source", "unknown"),
            description=result.get("description"),
            experience=result.get("experience"),
            posted_date=result.get("posted_date"),
        )

    def search(self, query: str) -> list[Job]:
        raise NotImplementedError(
            "A provider-specific search implementation must be connected."
        )