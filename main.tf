provider "aws" {
  region = var.aws_region
}

module "zero_trust" {
  source = "./modules/zero-trust"

  project_name = var.project_name
  aws_region   = var.aws_region
  vpc_cidr     = var.vpc_cidr
  tags         = var.tags
}

# Account-and-Region services. They sit in the root module because they are not VPC resources.
resource "aws_guardduty_detector" "main" {
  enable                       = true
  finding_publishing_frequency = "SIX_HOURS"
  tags                         = var.tags
}

resource "aws_securityhub_account" "main" {
  # CIS and Foundational Security Best Practices stay off. The NIST subscription below is the only standard.
  enable_default_standards = false
  auto_enable_controls     = true
}

data "aws_partition" "current" {}

data "aws_region" "current" {}

resource "aws_securityhub_standards_subscription" "nist_800_53_rev5" {
  depends_on    = [aws_securityhub_account.main]
  standards_arn = "arn:${data.aws_partition.current.partition}:securityhub:${data.aws_region.current.region}::standards/nist-800-53/v/5.0.0"
}
