output "vpc_id" {
  value       = module.zero_trust.vpc_id
  description = "VPC ID"
}

output "verified_access_instance_id" {
  value       = module.zero_trust.verified_access_instance_id
  description = "Verified Access instance ID"
}

output "guardduty_detector_id" {
  value       = aws_guardduty_detector.main.id
  description = "GuardDuty detector ID in the provider Region"
}

output "securityhub_nist_subscription_arn" {
  value       = aws_securityhub_standards_subscription.nist_800_53_rev5.arn
  description = "Security Hub subscription ARN for NIST SP 800-53 Rev. 5"
}
