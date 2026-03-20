output "ecr_repository_url" {
  description = "ECR repository URL for the backend image"
  value       = module.ecr.repository_url
}

output "backend_alb_dns" {
  description = "DNS name of the backend ALB"
  value       = module.ecs.alb_dns_name
}

output "frontend_bucket_name" {
  description = "S3 bucket name for the frontend"
  value       = module.frontend_hosting.bucket_name
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain name"
  value       = module.frontend_hosting.cloudfront_domain
}

output "dynamodb_table_name" {
  description = "DynamoDB table name"
  value       = module.dynamodb.table_name
}
