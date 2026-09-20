terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

provider "aws" {
  region = "ap-south-1"
}

variable "radar_schedule_enabled" {
  type        = bool
  description = "Enable the EventBridge Scheduler target. The target must be a private scheduler adapter Lambda."
  default     = false
}

variable "radar_schedule_expression" {
  type        = string
  description = "EventBridge Scheduler expression, for example rate(1 day)."
  default     = "rate(1 day)"
}

variable "radar_schedule_timezone" {
  type        = string
  description = "IANA timezone used by EventBridge Scheduler."
  default     = "Asia/Kolkata"
}

variable "radar_scheduler_target_lambda_arn" {
  type        = string
  description = "ARN of the privately deployed scheduler adapter Lambda that invokes JobRadar."
  default     = ""
}

variable "radar_queue_processor_lambda_arn" {
  type        = string
  description = "Optional private Lambda ARN that consumes discovery queue messages."
  default     = ""
}

variable "create_tavily_secret" {
  type        = bool
  description = "Create an empty Secrets Manager container for the deployed Tavily API key."
  default     = false
}

variable "tavily_secret_arn" {
  type        = string
  description = "Existing Secrets Manager ARN containing the Tavily API key."
  default     = ""
}

resource "aws_dynamodb_table" "jobradar_jobs" {
  name         = "jobradar-jobs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "job_id"

  attribute {
    name = "job_id"
    type = "S"
  }

  tags = {
    Project = "JobRadar"
  }
}

resource "aws_dynamodb_table" "jobradar_radar_locks" {
  name         = "jobradar-radar-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "lock_key"

  attribute {
    name = "lock_key"
    type = "S"
  }

  ttl {
    attribute_name = "lease_until"
    enabled        = true
  }

  tags = {
    Project = "JobRadar"
    Purpose = "Radar execution lease"
  }
}

resource "aws_s3_bucket" "jobradar_raw_discovery" {
  bucket_prefix = "jobradar-raw-discovery-"

  tags = {
    Project = "JobRadar"
    Purpose = "Raw discovery snapshots"
  }
}

resource "aws_s3_bucket_public_access_block" "jobradar_raw_discovery" {
  bucket = aws_s3_bucket.jobradar_raw_discovery.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "jobradar_raw_discovery" {
  bucket = aws_s3_bucket.jobradar_raw_discovery.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "jobradar_raw_discovery" {
  bucket = aws_s3_bucket.jobradar_raw_discovery.id

  rule {
    id     = "expire-raw-discovery"
    status = "Enabled"

    expiration {
      days = 30
    }
  }
}

resource "aws_sqs_queue" "jobradar_discovery_dlq" {
  name                      = "jobradar-discovery-dlq"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "jobradar_discovery" {
  name                       = "jobradar-discovery"
  visibility_timeout_seconds = 900
  message_retention_seconds  = 345600

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.jobradar_discovery_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_secretsmanager_secret" "tavily" {
  count       = var.create_tavily_secret ? 1 : 0
  name_prefix = "jobradar-tavily-"

  tags = {
    Project = "JobRadar"
    Purpose = "Tavily API key container"
  }
}

output "jobradar_raw_discovery_bucket" {
  value       = aws_s3_bucket.jobradar_raw_discovery.bucket
  description = "Set S3_RAW_DISCOVERY_BUCKET to this bucket for raw discovery capture."
}

output "jobradar_discovery_queue_url" {
  value       = aws_sqs_queue.jobradar_discovery.url
  description = "Set SQS_DISCOVERY_QUEUE_URL to this queue for optional async processing."
}

output "jobradar_discovery_dlq_url" {
  value       = aws_sqs_queue.jobradar_discovery_dlq.url
  description = "Discovery dead-letter queue URL."
}

output "jobradar_tavily_secret_arn" {
  value       = var.create_tavily_secret ? aws_secretsmanager_secret.tavily[0].arn : null
  description = "Set TAVILY_SECRET_ARN after storing TAVILY_API_KEY in the secret."
}

resource "aws_iam_policy" "jobradar_radar_lock" {
  name        = "jobradar-radar-lock-access"
  description = "Least-privilege access for the JobRadar execution lock."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:DeleteItem",
        "dynamodb:PutItem",
      ]
      Resource = aws_dynamodb_table.jobradar_radar_locks.arn
    }]
  })
}

resource "aws_iam_policy" "jobradar_runtime_event_driven" {
  name        = "jobradar-runtime-event-driven-access"
  description = "Least-privilege optional access for raw discovery, queueing, metrics, and Tavily secret lookup."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat([
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${aws_s3_bucket.jobradar_raw_discovery.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = aws_sqs_queue.jobradar_discovery.arn
      },
      {
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData"]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "JobRadar"
          }
        }
      },
      ], var.tavily_secret_arn != "" || var.create_tavily_secret ? [{
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = var.tavily_secret_arn != "" ? var.tavily_secret_arn : aws_secretsmanager_secret.tavily[0].arn
    }] : [])
  })
}

resource "aws_iam_policy" "jobradar_queue_processor" {
  name        = "jobradar-queue-processor-access"
  description = "Least-privilege SQS consume access for the optional discovery processor Lambda."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "sqs:DeleteMessage",
        "sqs:ReceiveMessage",
        "sqs:GetQueueAttributes",
      ]
      Resource = aws_sqs_queue.jobradar_discovery.arn
    }]
  })
}

output "jobradar_runtime_event_driven_policy_arn" {
  value       = aws_iam_policy.jobradar_runtime_event_driven.arn
  description = "Attach to the private backend/adapter runtime role when optional event-driven features are enabled."
}

output "jobradar_queue_processor_policy_arn" {
  value       = aws_iam_policy.jobradar_queue_processor.arn
  description = "Attach to the optional discovery queue processor Lambda execution role."
}

resource "aws_lambda_event_source_mapping" "jobradar_discovery" {
  count            = var.radar_queue_processor_lambda_arn != "" ? 1 : 0
  event_source_arn = aws_sqs_queue.jobradar_discovery.arn
  function_name    = var.radar_queue_processor_lambda_arn
  batch_size       = 10
  enabled          = true
}

resource "aws_cloudwatch_metric_alarm" "jobradar_run_failures" {
  alarm_name          = "jobradar-radar-run-failures"
  alarm_description   = "Radar runs are failing."
  namespace           = "JobRadar"
  metric_name         = "RadarRunFailure"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
}

output "jobradar_radar_lock_policy_arn" {
  description = "Attach this policy to the private scheduler adapter/backend execution role."
  value       = aws_iam_policy.jobradar_radar_lock.arn
}

resource "aws_iam_role" "jobradar_scheduler" {
  count = var.radar_schedule_enabled && var.radar_scheduler_target_lambda_arn != "" ? 1 : 0
  name  = "jobradar-eventbridge-scheduler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "jobradar_scheduler" {
  count = var.radar_schedule_enabled && var.radar_scheduler_target_lambda_arn != "" ? 1 : 0
  role  = aws_iam_role.jobradar_scheduler[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["lambda:InvokeFunction"]
      Resource = var.radar_scheduler_target_lambda_arn
    }]
  })
}

resource "aws_scheduler_schedule" "jobradar_radar" {
  count = var.radar_schedule_enabled && var.radar_scheduler_target_lambda_arn != "" ? 1 : 0
  name  = "jobradar-radar"

  schedule_expression          = var.radar_schedule_expression
  schedule_expression_timezone = var.radar_schedule_timezone

  flexible_time_window { mode = "OFF" }

  target {
    arn      = var.radar_scheduler_target_lambda_arn
    role_arn = aws_iam_role.jobradar_scheduler[0].arn
    input    = jsonencode({ trigger = "scheduled" })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }
}
