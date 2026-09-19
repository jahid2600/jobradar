import os
import re

from tavily import TavilyClient
from urllib.parse import urlparse

from backend.discovery.web_search_provider import WebSearchProvider


class TavilySearchProvider(WebSearchProvider):
    """Real web search provider powered by Tavily."""

    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")

        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set.")

        self.client = TavilyClient(api_key=api_key)

    @staticmethod
    def _extract_location(text: str) -> str:
        text_lower = text.lower()

        if "bengaluru" in text_lower or "bangalore" in text_lower:
            return "Bengaluru"

        return ""

    @staticmethod
    def _extract_experience(text: str) -> str:
        patterns = [
            r"\b(?:0|zero)\s*[-–]\s*1\s*years?\b",
            r"\b1\s*[-–]\s*2\s*years?\b",
            r"\b(?:fresher|freshers)\b",
            r"\b(?:entry[- ]level)\b",
            r"\b(?:graduate|graduates)\b",
            r"\b(?:intern|internship)\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)

        return ""

    @staticmethod
    def _extract_company(title: str, content: str, url: str) -> str:
        # Common search-result patterns such as:
        # "AWS Cloud Engineer at Example Corp"
        match = re.search(
            r"\bat\s+([A-Z][A-Za-z0-9&.,' -]{2,80})",
            title,
        )

        if match:
            return match.group(1).strip(" -|")

        # Some job pages mention "Company: Example Corp".
        match = re.search(
            r"(?:company|employer)\s*:\s*([A-Z][A-Za-z0-9&.,' -]{2,80})",
            content,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).strip(" -|.")

        # Recognize common company names when they appear in the result.
        known_companies = (
            "TCS",
            "Tata Consultancy Services",
            "Amazon",
            "AWS",
            "Microsoft",
            "Google",
            "Tesco",
            "Infosys",
            "Wipro",
            "Accenture",
            "Cognizant",
            "Capgemini",
        )

        combined = f"{title} {content}"

        for company in known_companies:
            if re.search(rf"\b{re.escape(company)}\b", combined, re.IGNORECASE):
                return company

        # Last-resort identifier from the hosting domain.
        hostname = urlparse(url).netloc.lower().removeprefix("www.")

        if hostname and hostname not in {
            "linkedin.com",
            "indeed.com",
            "naukri.com",
        }:
            return hostname.split(".")[0].replace("-", " ").title()

        return ""

    def search(self, query: str):
        response = self.client.search(
            query=query,
            max_results=5,
            search_depth="advanced",
        )

        results = []

        for item in response.get("results", []):
            title = item.get("title", "")
            content = item.get("content", "")
            combined_text = f"{title} {content}"

            results.append({
                "title": title,
                "company": self._extract_company(title, content, item.get("url", "")),
                "location": self._extract_location(combined_text),
                "url": item.get("url", ""),
                "source": "tavily",
                "description": content,
                "experience": self._extract_experience(combined_text),
            })

        return self.normalize_results(results)
