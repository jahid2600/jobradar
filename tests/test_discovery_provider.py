from backend.discovery.mock_search_provider import MockSearchProvider


def test_mock_search_provider_returns_jobs():
    provider = MockSearchProvider()

    jobs = provider.search("AWS Cloud Engineer Bengaluru")

    assert len(jobs) == 2

    for job in jobs:
        assert job.title
        assert job.company
        assert job.location
        assert job.url
        assert job.source


def test_mock_search_provider_normalizes_job_objects():
    provider = MockSearchProvider()

    jobs = provider.search("DevOps")

    assert jobs[0].location == "Bengaluru"
    assert jobs[0].source == "mock"