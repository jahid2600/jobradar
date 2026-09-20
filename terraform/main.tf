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
