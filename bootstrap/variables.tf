variable "aws_region" {
  description = "AWS region for the state bucket and KMS key"
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Globally unique name for the Terraform state bucket. There is no default, because the name is account-specific."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "Bucket name must be 3-63 characters: lowercase letters, numbers, and hyphens, starting and ending with a letter or number."
  }
}

variable "kms_alias_name" {
  description = "Alias for the state KMS key, without the alias/ prefix"
  type        = string
  default     = "zero-trust-terraform-state"

  validation {
    condition     = can(regex("^[a-zA-Z0-9/_-]{1,256}$", var.kms_alias_name))
    error_message = "KMS alias name must be 1-256 characters and contain only letters, numbers, underscores, hyphens, or slashes."
  }
}

variable "tags" {
  description = "Tags applied to the state bucket and KMS key"
  type        = map(string)
  default = {
    Project     = "Zero-Trust"
    Environment = "Lab"
    Owner       = "Marlon Garcia"
    Purpose     = "terraform-state"
    ManagedBy   = "Terraform"
  }
}
