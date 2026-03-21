terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

module "ecr" {
  source       = "./modules/ecr"
  project_name = var.project_name
}

module "dynamodb" {
  source       = "./modules/dynamodb"
  project_name = var.project_name
}

module "s3" {
  source          = "./modules/s3"
  project_name    = var.project_name
  expiration_days = var.s3_results_expiration_days
}

# --- IAM: Backend instance role (DynamoDB + Secrets Manager) ---

resource "aws_iam_role" "backend_instance" {
  name = "${var.project_name}-apprunner-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "dynamodb_access" {
  name = "${var.project_name}-dynamodb-access"
  role = aws_iam_role.backend_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:DescribeTable",
        ]
        Resource = [
          module.dynamodb.table_arn,
          "${module.dynamodb.table_arn}/index/*",
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "s3_results_access" {
  name = "${var.project_name}-s3-results-access"
  role = aws_iam_role.backend_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
        ]
        Resource = "${module.s3.bucket_arn}/results/*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "secrets_access" {
  name = "${var.project_name}-secrets-access"
  role = aws_iam_role.backend_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [var.secrets_manager_secret_arn]
      }
    ]
  })
}

# --- App Runner Services ---

module "backend" {
  source             = "./modules/apprunner"
  project_name       = var.project_name
  service_name       = "backend"
  ecr_repository_url = module.ecr.backend_repository_url
  image_tag          = var.backend_image_tag
  port               = "8080"
  cpu                = var.backend_cpu
  memory             = var.backend_memory
  instance_role_arn  = aws_iam_role.backend_instance.arn
  health_check_path  = "/health"
  health_check_protocol = "HTTP"
  environment_variables = {
    DYNAMODB_TABLE_NAME   = module.dynamodb.table_name
    AWS_REGION            = var.aws_region
    LLM_PROVIDER          = var.llm_provider
    LOG_LEVEL             = "INFO"
    FRONTEND_URL          = "https://${module.frontend.service_url}"
    S3_RESULTS_BUCKET     = module.s3.bucket_name
  }
  environment_secrets = {
    OPENAI_API_KEY = "${var.secrets_manager_secret_arn}:OPENAI_API_KEY::"
  }
}

module "frontend" {
  source             = "./modules/apprunner"
  project_name       = var.project_name
  service_name       = "frontend"
  ecr_repository_url = module.ecr.frontend_repository_url
  image_tag          = var.frontend_image_tag
  port               = "80"
  cpu                = "256"
  memory             = "512"
}
