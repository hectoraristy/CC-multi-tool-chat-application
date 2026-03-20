variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "multi-tool-chat"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "backend_image_tag" {
  description = "Docker image tag for the backend"
  type        = string
  default     = "latest"
}

variable "backend_cpu" {
  description = "CPU units for backend Fargate task"
  type        = number
  default     = 512
}

variable "backend_memory" {
  description = "Memory (MiB) for backend Fargate task"
  type        = number
  default     = 1024
}

variable "backend_desired_count" {
  description = "Number of backend task instances"
  type        = number
  default     = 1
}

variable "secrets_manager_secret_arn" {
  description = "ARN of the Secrets Manager secret containing app credentials (JSON with OPENAI_API_KEY)"
  type        = string
}

variable "llm_provider" {
  description = "LLM provider (openai, anthropic, bedrock)"
  type        = string
  default     = "openai"
}
