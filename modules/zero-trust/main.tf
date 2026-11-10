# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = merge(var.tags, { Name = "${var.project_name}-vpc" })
}

# Private Subnets
resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + 1)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags              = merge(var.tags, { Name = "${var.project_name}-private-${count.index + 1}" })
}

data "aws_availability_zones" "available" {}

# AWS Verified Access
resource "aws_verifiedaccess_instance" "main" {
  description = "Zero Trust Verified Access Instance"
  tags        = var.tags
}

resource "aws_verifiedaccess_trust_provider" "device" {
  description                = "Device Trust Provider"
  policy_reference_name      = "device-trust"
  trust_provider_type        = "device"
  device_trust_provider_type = "jamf"
  tags                       = var.tags
}

resource "aws_verifiedaccess_instance_trust_provider_attachment" "main" {
  verifiedaccess_instance_id       = aws_verifiedaccess_instance.main.id
  verifiedaccess_trust_provider_id = aws_verifiedaccess_trust_provider.device.id
}

# Endpoint in the first private subnet. The policy attaches no rule groups.
resource "aws_networkfirewall_firewall" "main" {
  name                = "${var.project_name}-firewall"
  firewall_policy_arn = aws_networkfirewall_firewall_policy.main.arn
  vpc_id              = aws_vpc.main.id
  subnet_mapping {
    subnet_id = aws_subnet.private[0].id
  }
  tags = var.tags
}

resource "aws_networkfirewall_firewall_policy" "main" {
  name = "${var.project_name}-firewall-policy"
  firewall_policy {
    stateless_default_actions          = ["aws:forward_to_sfe"]
    stateless_fragment_default_actions = ["aws:forward_to_sfe"]
  }
  tags = var.tags
}
