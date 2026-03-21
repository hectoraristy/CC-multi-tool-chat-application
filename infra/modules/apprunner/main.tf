variable "project_name" {
  type = string
}

variable "service_name" {
  description = "Service identifier (e.g. backend, frontend)"
  type        = string
}

variable "ecr_repository_url" {
  type = string
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "port" {
  description = "Container port the service listens on"
  type        = string
}

variable "cpu" {
  type    = string
  default = "512"
}

variable "memory" {
  type    = string
  default = "1024"
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "environment_secrets" {
  type    = map(string)
  default = {}
}

variable "health_check_path" {
  type    = string
  default = null
}

variable "health_check_protocol" {
  type    = string
  default = "TCP"
}

variable "instance_role_arn" {
  type    = string
  default = null
}

variable "auto_deployments_enabled" {
  description = "Whether App Runner automatically deploys when a new image is pushed to ECR"
  type        = bool
  default     = true
}

# --- IAM: ECR access role for App Runner ---

resource "aws_iam_role" "ecr_access" {
  name = "${var.project_name}-${var.service_name}-apprunner-ecr"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecr_access" {
  role       = aws_iam_role.ecr_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# --- App Runner Service ---

resource "aws_apprunner_service" "this" {
  service_name = "${var.project_name}-${var.service_name}"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.ecr_access.arn
    }

    image_repository {
      image_identifier      = "${var.ecr_repository_url}:${var.image_tag}"
      image_repository_type = "ECR"

      image_configuration {
        port                          = var.port
        runtime_environment_variables = length(var.environment_variables) > 0 ? var.environment_variables : null
        runtime_environment_secrets   = length(var.environment_secrets) > 0 ? var.environment_secrets : null
      }
    }

    auto_deployments_enabled = var.auto_deployments_enabled
  }

  instance_configuration {
    cpu               = var.cpu
    memory            = var.memory
    instance_role_arn = var.instance_role_arn
  }

  dynamic "health_check_configuration" {
    for_each = var.health_check_path != null ? [1] : []
    content {
      protocol            = var.health_check_protocol
      path                = var.health_check_path
      healthy_threshold   = 2
      unhealthy_threshold = 3
      interval            = 10
    }
  }

  tags = {
    Name = "${var.project_name}-${var.service_name}"
  }
}

# --- Outputs ---

output "service_url" {
  value = aws_apprunner_service.this.service_url
}

output "service_arn" {
  value = aws_apprunner_service.this.arn
}

output "service_id" {
  value = aws_apprunner_service.this.service_id
}
