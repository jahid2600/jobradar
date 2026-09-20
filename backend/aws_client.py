import boto3

from backend.config import (
    BEDROCK_REGION,
    CLOUDWATCH_REGION,
    DYNAMODB_REGION,
    S3_REGION,
    SNS_REGION,
    SQS_REGION,
)

bedrock_runtime = boto3.client(
    "bedrock-runtime",
    region_name=BEDROCK_REGION,
)

s3 = boto3.client(
    "s3",
    region_name=S3_REGION,
)

dynamodb = boto3.client(
    "dynamodb",
    region_name=DYNAMODB_REGION,
)

sqs = boto3.client(
    "sqs",
    region_name=SQS_REGION,
)

sns = boto3.client(
    "sns",
    region_name=SNS_REGION,
)

cloudwatch = boto3.client(
    "cloudwatch",
    region_name=CLOUDWATCH_REGION,
)

secretsmanager = boto3.client(
    "secretsmanager",
    region_name=BEDROCK_REGION,
)

print("JobRadar AWS clients initialized successfully.")