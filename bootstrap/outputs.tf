output "bucket_name" {
  description = "State bucket name. Copy this to bucket in backend.hcl."
  value       = aws_s3_bucket.state.id
}

output "bucket_region" {
  description = "State bucket region. Copy this to region in backend.hcl."
  value       = var.aws_region
}

output "kms_key_arn" {
  description = "Customer-managed key ARN. Copy this to kms_key_id in backend.hcl."
  value       = aws_kms_key.state.arn
}

output "kms_alias_arn" {
  description = "Alias ARN for the state key"
  value       = aws_kms_alias.state.arn
}
