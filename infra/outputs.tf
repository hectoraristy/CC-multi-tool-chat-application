output "ecr_backend_repository_url" {
  description = "ECR repository URL for the backend image"
  value       = module.ecr.backend_repository_url
}

output "ecr_frontend_repository_url" {
  description = "ECR repository URL for the frontend image"
  value       = module.ecr.frontend_repository_url
}

output "backend_url" {
  description = "App Runner service URL for the backend"
  value       = module.backend.service_url
}

output "frontend_url" {
  description = "App Runner service URL for the frontend"
  value       = module.frontend.service_url
}

output "backend_service_arn" {
  description = "App Runner service ARN for the backend (used in CI/CD)"
  value       = module.backend.service_arn
}

output "frontend_service_arn" {
  description = "App Runner service ARN for the frontend (used in CI/CD)"
  value       = module.frontend.service_arn
}

output "dynamodb_table_name" {
  description = "DynamoDB table name"
  value       = module.dynamodb.table_name
}
