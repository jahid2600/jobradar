import boto3

from backend.config import BEDROCK_REGION, DYNAMODB_REGION, SNS_REGION

bedrock_runtime = boto3.client(
    "bedrock-runtime",
    region_name=BEDROCK_REGION,
)

s3 = boto3.client(
    "s3",
    region_name=BEDROCK_REGION,
)

dynamodb = boto3.client(
    "dynamodb",
    region_name=DYNAMODB_REGION,
)

sqs = boto3.client(
    "sqs",
    region_name=BEDROCK_REGION,
)

sns = boto3.client(
    "sns",
    region_name=SNS_REGION,
)

print("JobRadar AWS clients initialized successfully.")