import os


BEDROCK_REGION = os.getenv(
    "AWS_BEDROCK_REGION",
    os.getenv("AWS_REGION", "us-east-1"),
)
DYNAMODB_REGION = os.getenv("AWS_DYNAMODB_REGION", "ap-south-1")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "jobradar-jobs")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "deepseek.v3.2")

HARD_MAX_SEARCH_QUERIES = 8
HARD_MAX_TAVILY_RESULTS_PER_QUERY = 10
HARD_MAX_DISCOVERY_RESULTS = 50
HARD_MAX_QUALIFICATION_CANDIDATES = 50


def _bounded_int(name: str, default: int, maximum: int) -> int:
    try:
        configured = int(os.getenv(name, str(default)))
    except ValueError:
        configured = default
    return max(1, min(configured, maximum))


TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_MAX_RESULTS = _bounded_int(
    "TAVILY_MAX_RESULTS",
    5,
    HARD_MAX_TAVILY_RESULTS_PER_QUERY,
)
TAVILY_SEARCH_DEPTH = os.getenv("TAVILY_SEARCH_DEPTH", "advanced")
SEARCH_STRATEGY_MAX_QUERIES = _bounded_int(
    "SEARCH_STRATEGY_MAX_QUERIES",
    HARD_MAX_SEARCH_QUERIES,
    HARD_MAX_SEARCH_QUERIES,
)

# Kept for compatibility with existing imports and local configuration.
AWS_REGION = BEDROCK_REGION

JOBRADAR_NAME = "JobRadar"

TARGET_LOCATION = "Bengaluru"

TARGET_EXPERIENCE = "0-1 years"

TARGET_ROLES = [
    "AWS Cloud Engineer",
    "AWS Cloud Support Engineer",
    "Cloud Support Associate",
    "Cloud Operations Engineer",
    "Cloud Infrastructure Engineer",
    "Junior DevOps Engineer",
    "Cloud Administrator",
    "Entry-level SRE",
    "DevOps Intern",
    "Cloud Intern",
]

TARGET_SKILLS = [
    "AWS",
    "Linux",
    "Docker",
    "Git",
    "Python",
    "Terraform",
    "CI/CD",
]

PREFERRED_COMPANY_TYPES = [
    "MNC",
    "Startup",
    "Internship",
    "Entry-level",
]