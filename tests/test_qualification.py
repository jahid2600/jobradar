from backend.discovery.job_schema import Job
from backend.intelligence.qualification import QualificationEngine


engine = QualificationEngine()


def test_strong_aws_cloud_match():
    job = Job(
        title="Junior AWS Cloud Engineer",
        company="Test Cloud",
        location="Bengaluru",
        url="https://example.com/1",
        source="test",
        description="AWS, Linux, Python, Docker and Terraform.",
        experience="0-1 years",
    )

    result = engine.evaluate(job)

    assert result.qualified is True
    assert result.score >= 60


def test_devops_entry_level_match():
    job = Job(
        title="DevOps Intern",
        company="Test Systems",
        location="Bengaluru",
        url="https://example.com/2",
        source="test",
        description="Linux, Docker, Git and CI/CD.",
        experience="Fresher",
    )

    result = engine.evaluate(job)

    assert result.qualified is True


def test_wrong_location():
    job = Job(
        title="AWS Cloud Engineer",
        company="Test Cloud",
        location="Mumbai",
        url="https://example.com/3",
        source="test",
        description="AWS and Linux.",
        experience="0-1 years",
    )

    result = engine.evaluate(job)

    assert result.qualified is False


def test_senior_role():
    job = Job(
        title="Senior AWS Cloud Engineer",
        company="Test Cloud",
        location="Bengaluru",
        url="https://example.com/4",
        source="test",
        description="AWS, Linux, Terraform and Kubernetes.",
        experience="5+ years",
    )

    result = engine.evaluate(job)

    assert result.qualified is False


def test_unrelated_role():
    job = Job(
        title="Frontend Developer",
        company="Test Software",
        location="Bengaluru",
        url="https://example.com/5",
        source="test",
        description="React, JavaScript and CSS.",
        experience="0-1 years",
    )

    result = engine.evaluate(job)

    assert result.qualified is False