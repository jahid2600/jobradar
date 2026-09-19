import boto3

AWS_REGION = "us-east-1"

bedrock_runtime = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION
)

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION
)

dynamodb = boto3.client(
    "dynamodb",
    region_name="ap-south-1"
)

sqs = boto3.client(
    "sqs",
    region_name=AWS_REGION
)

sns = boto3.client(
    "sns",
    region_name=AWS_REGION
)

print("JobRadar AWS clients initialized successfully.")