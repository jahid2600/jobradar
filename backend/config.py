import os


BEDROCK_REGION = os.getenv(
    "AWS_BEDROCK_REGION",
    os.getenv("AWS_REGION", "us-east-1"),
)
DYNAMODB_REGION = os.getenv("AWS_DYNAMODB_REGION", "ap-south-1")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "jobradar-jobs")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "deepseek.v3.2")
SNS_ENABLED = os.getenv("SNS_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN")
SNS_REGION = os.getenv("SNS_REGION", BEDROCK_REGION)
S3_RAW_DISCOVERY_ENABLED = os.getenv("S3_RAW_DISCOVERY_ENABLED", "false").strip().lower() in {
    "1", "true", "yes", "on",
}
S3_REGION = os.getenv("S3_REGION", BEDROCK_REGION)
S3_RAW_DISCOVERY_BUCKET = os.getenv("S3_RAW_DISCOVERY_BUCKET")
S3_RAW_DISCOVERY_PREFIX = os.getenv("S3_RAW_DISCOVERY_PREFIX", "raw-discovery")
SQS_ENABLED = os.getenv("SQS_ENABLED", "false").strip().lower() in {
    "1", "true", "yes", "on",
}
SQS_ASYNC_PROCESSING = os.getenv("SQS_ASYNC_PROCESSING", "false").strip().lower() in {
    "1", "true", "yes", "on",
}
SQS_DISCOVERY_QUEUE_URL = os.getenv("SQS_DISCOVERY_QUEUE_URL")
SQS_REGION = os.getenv("SQS_REGION", BEDROCK_REGION)
SQS_VISIBILITY_TIMEOUT_SECONDS = int(os.getenv("SQS_VISIBILITY_TIMEOUT_SECONDS", "900"))
SQS_MAX_RECEIVE_COUNT = int(os.getenv("SQS_MAX_RECEIVE_COUNT", "3"))
CLOUDWATCH_METRICS_ENABLED = os.getenv("CLOUDWATCH_METRICS_ENABLED", "false").strip().lower() in {
    "1", "true", "yes", "on",
}
CLOUDWATCH_METRICS_NAMESPACE = os.getenv("CLOUDWATCH_METRICS_NAMESPACE", "JobRadar")
CLOUDWATCH_REGION = os.getenv("CLOUDWATCH_REGION", BEDROCK_REGION)
TAVILY_SECRET_ARN = os.getenv("TAVILY_SECRET_ARN")
RADAR_SCHEDULE_ENABLED = os.getenv("RADAR_SCHEDULE_ENABLED", "false").strip().lower() in {
    "1", "true", "yes", "on",
}
RADAR_SCHEDULE_EXPRESSION = os.getenv("RADAR_SCHEDULE_EXPRESSION", "rate(1 day)")
RADAR_SCHEDULE_TIMEZONE = os.getenv("RADAR_SCHEDULE_TIMEZONE", "Asia/Kolkata")
RADAR_LOCK_ENABLED = os.getenv("RADAR_LOCK_ENABLED", "false").strip().lower() in {
    "1", "true", "yes", "on",
}
RADAR_LOCK_TABLE_NAME = os.getenv("RADAR_LOCK_TABLE_NAME", "jobradar-radar-locks")
RADAR_LOCK_KEY = os.getenv("RADAR_LOCK_KEY", "radar-execution")
RADAR_LOCK_LEASE_SECONDS = int(os.getenv("RADAR_LOCK_LEASE_SECONDS", "3600"))

HARD_MAX_SEARCH_QUERIES = 8
HARD_MAX_TAVILY_RESULTS_PER_QUERY = 10
HARD_MAX_DISCOVERY_RESULTS = 50
HARD_MAX_QUALIFICATION_CANDIDATES = 50
MAX_RADAR_RUN_HISTORY = 25
RADAR_RUNS_FILE = os.getenv("RADAR_RUNS_FILE", "data/radar_runs.json")


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