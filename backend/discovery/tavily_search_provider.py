import re
import logging
import json

from tavily import TavilyClient
from urllib.parse import urlparse

from backend.config import (
    TAVILY_API_KEY,
    TAVILY_MAX_RESULTS,
    TAVILY_SEARCH_DEPTH,
    TAVILY_SECRET_ARN,
)
from backend.aws_client import secretsmanager
from backend.discovery.web_search_provider import WebSearchProvider


logger = logging.getLogger(__name__)


class TavilySearchProvider(WebSearchProvider):
    """Real web search provider powered by Tavily."""

    def __init__(self):
        api_key = TAVILY_API_KEY or self._load_secret_key()
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set.")

        self.client = TavilyClient(api_key=api_key)
        self.last_failures = []

    @staticmethod
    def _load_secret_key():
        if not TAVILY_SECRET_ARN:
            return None
        try:
            response = secretsmanager.get_secret_value(SecretId=TAVILY_SECRET_ARN)
            secret = response.get("SecretString", "")
            try:
                parsed = json.loads(secret)
                return parsed.get("TAVILY_API_KEY") or parsed.get("api_key")
            except json.JSONDecodeError:
                return secret or None
        except Exception:
            logger.exception("Tavily secret lookup failed")
            return None

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
        _, jobs = self.search_with_raw(query)
        return jobs

    def search_with_raw(self, query: str):
        self.last_failures = []
        response = self.client.search(
            query=query,
            max_results=TAVILY_MAX_RESULTS,
            search_depth=TAVILY_SEARCH_DEPTH,
        )

        raw_results = response.get("results", [])
        results = []

        for item in raw_results:
            if not isinstance(item, dict):
                self.last_failures.append("malformed Tavily result skipped")
                logger.warning("Malformed Tavily result skipped")
                continue

            title = str(item.get("title", "") or "")
            content = str(item.get("content", "") or "")
            url = str(item.get("url", "") or "")
            if not title or not url:
                self.last_failures.append("malformed Tavily result missing title or URL")
                logger.warning("Malformed Tavily result missing title or URL")
                continue
            combined_text = f"{title} {content}"

            results.append({
                "title": title,
                "company": self._extract_company(title, content, url),
                "location": self._extract_location(combined_text),
                "url": url,
                "source": "tavily",
                "description": content,
                "experience": self._extract_experience(combined_text),
            })

        return raw_results, self.normalize_results(results)
