variable "project_name" {
  type = string
}

resource "aws_dynamodb_table" "tool_results" {
  name         = "${var.project_name}-tool-results"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-tool-results"
  }
}

output "table_name" {
  value = aws_dynamodb_table.tool_results.name
}

output "table_arn" {
  value = aws_dynamodb_table.tool_results.arn
}

output "table_endpoint_url" {
  value = aws_dynamodb_table.tool_results.endpoint_url
}