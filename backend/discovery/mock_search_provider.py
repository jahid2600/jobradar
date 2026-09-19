from backend.discovery.web_search_provider import WebSearchProvider


class MockSearchProvider(WebSearchProvider):
    """Temporary provider used to test JobRadar's discovery pipeline."""

    def search(self, query: str):
        raw_results = [
            {
                "title": "Junior AWS Cloud Engineer",
                "company": "Example Cloud Technologies",
                "location": "Bengaluru",
                "url": "https://example.com/jobs/junior-aws-cloud-engineer",
                "source": "mock",
                "description": (
                    "Entry-level cloud engineering role requiring AWS, "
                    "Linux, Python and basic DevOps knowledge."
                ),
                "experience": "0-1 years",
                "posted_date": "2026-09-19",
            },
            {
                "title": "DevOps Intern",
                "company": "Example Systems",
                "location": "Bengaluru",
                "url": "https://example.com/jobs/devops-intern",
                "source": "mock",
                "description": (
                    "DevOps internship involving Linux, Git, Docker "
                    "and CI/CD."
                ),
                "experience": "Fresher",
                "posted_date": "2026-09-19",
            },
        ]

        return self.normalize_results(raw_results)