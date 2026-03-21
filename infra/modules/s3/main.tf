variable "project_name" {
  type = string
}

variable "expiration_days" {
  description = "Days before tool result objects are automatically deleted"
  type        = number
  default     = 30
}

resource "aws_s3_bucket" "tool_results" {
  bucket = "${var.project_name}-tool-results"

  tags = {
    Name = "${var.project_name}-tool-results"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "tool_results" {
  bucket = aws_s3_bucket.tool_results.id

  rule {
    id     = "expire-old-results"
    status = "Enabled"

    filter {
      prefix = "results/"
    }

    expiration {
      days = var.expiration_days
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tool_results" {
  bucket = aws_s3_bucket.tool_results.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tool_results" {
  bucket = aws_s3_bucket.tool_results.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

output "bucket_name" {
  value = aws_s3_bucket.tool_results.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.tool_results.arn
}
