variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "zero-trust-demo"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "tags" {
  description = "Tags applied to resources that accept tags"
  type        = map(string)
  default = {
    Project     = "Zero-Trust"
    Environment = "Lab"
    Owner       = "Marlon Garcia"
    Compliance  = "portfolio-lab"
    ManagedBy   = "Terraform"
  }
}
