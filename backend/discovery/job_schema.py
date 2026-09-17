from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    source: str

    description: Optional[str] = None
    experience: Optional[str] = None
    posted_date: Optional[str] = None

    def to_dict(self):
        return asdict(self)


if __name__ == "__main__":
    sample_job = Job(
        title="AWS Cloud Engineer",
        company="Example Company",
        location="Bengaluru",
        url="https://example.com/job",
        source="example",
        description="Entry-level AWS Cloud Engineer opportunity.",
        experience="0-1 years",
    )

    print(sample_job.to_dict())