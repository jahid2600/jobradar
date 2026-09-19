import os

from tavily import TavilyClient

from backend.discovery.web_search_provider import WebSearchProvider


class TavilySearchProvider(WebSearchProvider):
    """Real web search provider powered by Tavily."""

    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")

        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set.")

        self.client = TavilyClient(api_key=api_key)

    def search(self, query: str):
        response = self.client.search(
            query=query,
            max_results=min(5, 5),
            search_depth="advanced",
        )

        results = []

        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "company": "",
                "location": "",
                "url": item.get("url", ""),
                "source": "tavily",
                "description": item.get("content", ""),
            })

        return self.normalize_results(results)
