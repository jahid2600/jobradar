from backend.discovery.real_search_provider import RealSearchProvider


class FakeSearchClient:
    def search(self, query: str):
        return [
            {
                "title": "AWS Cloud Engineer",
                "company": "Test Cloud",
                "location": "Bengaluru",
                "url": "https://example.com/job",
                "source": "fake-search",
                "description": "AWS and Linux role for freshers.",
                "experience": "0-1 years",
            }
        ]


def test_real_search_provider_normalizes_results():
    provider = RealSearchProvider(FakeSearchClient())

    jobs = provider.search("AWS Cloud Engineer Bengaluru")

    assert len(jobs) == 1
    assert jobs[0].title == "AWS Cloud Engineer"
    assert jobs[0].company == "Test Cloud"
    assert jobs[0].location == "Bengaluru"
    assert jobs[0].source == "fake-search"