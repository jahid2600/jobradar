from typing import Any

from backend.discovery.web_search_provider import WebSearchProvider


class RealSearchProvider(WebSearchProvider):
    """Base implementation for connecting a real web-search backend."""

    def __init__(self, search_client: Any):
        self.search_client = search_client

    def search(self, query: str):
        """
        Execute a search using the configured search client.

        The search client is intentionally injected so JobRadar
        stays independent of a specific search provider.
        """
        raw_results = self.search_client.search(query)

        return self.normalize_results(raw_results)