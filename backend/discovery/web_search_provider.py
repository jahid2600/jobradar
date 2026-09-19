from typing import Any

from backend.discovery.discovery_adapter import RawResultAdapter
from backend.discovery.job_schema import Job


class WebSearchProvider(RawResultAdapter):
    """Provider interface for web-based job discovery."""

    def search(self, query: str) -> list[Job]:
        """
        Search the web for jobs.

        The actual web-search implementation will be connected later.
        For now, this class defines the provider boundary.
        """
        raise NotImplementedError(
            "Web search provider is not connected yet."
        )

    def normalize_results(self, results: list[dict[str, Any]]) -> list[Job]:
        """Convert multiple raw search results into Job objects."""
        return [self.normalize(result) for result in results]