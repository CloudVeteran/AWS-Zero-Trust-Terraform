# Zero Trust Cloud Architecture on AWS (Terraform)

[![Terraform](https://github.com/CloudVeteran/AWS-Zero-Trust-Terraform/actions/workflows/terraform.yml/badge.svg?branch=main)](https://github.com/CloudVeteran/AWS-Zero-Trust-Terraform/actions/workflows/terraform.yml)

Terraform for a small AWS lab: a VPC with three private subnets, an AWS Verified Access instance with a Jamf device trust provider, a Network Firewall, a GuardDuty detector, and Security Hub CSPM subscribed to NIST SP 800-53 Rev. 5.

Portfolio project by Marlon Garcia, AWS Certified Solutions Architect and CompTIA Security+.

![One AWS account in a single Region: a private VPC 10.0.0.0/16 with three private subnets, a Network Firewall endpoint in the first subnet that has no rules and no traffic routed to it, a Verified Access instance attached only to a Jamf device trust provider, and GuardDuty sending findings to Security Hub for NIST SP 800-53 Rev. 5.](docs/architecture.png)

*How to read this: the gray box is one AWS account, the green box is a private network with no internet gateway, the firewall sits in subnet 1 and does not inspect traffic, the Jamf check is not connected to an app, and GuardDuty sends findings to Security Hub.*

## Status and scope

This is a lab and portfolio project, not a production architecture. It is not an authority to operate, a FedRAMP package, or a complete Zero Trust design. The control table lists NIST SP 800-53 Rev. 5 controls these resources can support. A row in that table is not a control implementation statement, and it is not evidence that the control is satisfied. The CISA section maps the same resources to the five pillars in CISA's Zero Trust Maturity Model v2.0. It does not assign a maturity stage.

## Quick start

Clone the repo and run these from the repository root. They need no AWS credentials and create no resources.

```bash
terraform fmt -check
terraform init -backend=false
terraform validate
```

`terraform plan` and `terraform apply` need AWS credentials. Network Firewall and Verified Access are billable. Default tags set `Environment` to `Lab`.

Copy `terraform.tfvars.example` to `terraform.tfvars` to override the Region, project name, or VPC CIDR. `terraform.tfvars` is gitignored.

### Two-step init

The main stack stores state in S3. `backend.tf` sets `encrypt = true` and native S3 locking with `use_lockfile = true` (a `.tflock` object next to the state, not a DynamoDB table). The bucket name, Region, and KMS key ARN are account-specific, so they stay out of the repo. `terraform init -backend=false` skips that backend. CI uses it. A real init is the second step below.

Step 1 creates the bucket. `bootstrap/` has no backend block, so its state stays local. It creates a versioned S3 bucket, a customer-managed KMS key with rotation and a 30-day deletion window, default encryption SSE-KMS using that key, a public access block (all four settings), and a bucket policy that denies `s3:*` when `aws:SecureTransport` is false. The key alias defaults to `alias/zero-trust-terraform-state`. Set `kms_alias_name` in `terraform.tfvars` if that alias is already in the account. The key policy allows the account root; the caller still needs IAM permission to use the key.

```bash
cd bootstrap
terraform init
cp terraform.tfvars.example terraform.tfvars
# Set bucket_name to a globally unique name, then:
terraform apply
cd ..
```

Step 2 points the main stack at that bucket. Copy `backend.hcl.example` to `backend.hcl` and set `bucket`, `region`, and `kms_key_id` from the bootstrap outputs `bucket_name`, `bucket_region`, and `kms_key_arn`. `kms_key_id` has to be the key ARN. `backend.hcl` is gitignored. The state object key stays `zero-trust/terraform.tfstate` in `backend.tf`.

```bash
cp backend.hcl.example backend.hcl
terraform init -backend-config=backend.hcl
```

Passing `kms_key_id` makes Terraform encrypt the state and lock objects with that customer-managed key. `encrypt = true` without `kms_key_id` still encrypts, and Terraform then requests SSE-S3 (`AES256`), which does not use the key from `bootstrap/`.

Keep the local state under `bootstrap/`. That file is the state for the bucket and the key. It is not stored in the S3 backend. The identity you use needs permission to create those resources, then `s3:ListBucket` on the bucket, `s3:GetObject` and `s3:PutObject` on the state object, `s3:GetObject`, `s3:PutObject`, and `s3:DeleteObject` on the lock object, and `kms:Encrypt`, `kms:Decrypt`, and `kms:GenerateDataKey` on the key.

## Architecture

GuardDuty and Security Hub are account-and-Region services. The VPC resources are in `modules/zero-trust`. When both services are enabled in the same account and Region, GuardDuty sends its findings to Security Hub on its own. There is no `aws_securityhub_product_subscription` in this repo.

```mermaid
flowchart TB
    subgraph Account["One AWS account, one Region"]
        direction TB

        subgraph Monitoring["Watches the account"]
            direction LR
            GuardDuty["Threat detection<br/>(GuardDuty)"]
            SecurityHub["Compliance checks:<br/>NIST 800-53 Rev. 5<br/>(Security Hub)"]
        end

        GuardDuty -->|sends findings| SecurityHub

        subgraph VPC["Private network 10.0.0.0/16<br/>No internet gateway"]
            direction TB
            Subnet1["Private subnet 1<br/>10.0.16.0/20, zone 1"]
            Subnet2["Private subnet 2<br/>10.0.32.0/20, zone 2"]
            Subnet3["Private subnet 3<br/>10.0.48.0/20, zone 3"]
            Firewall["Network Firewall<br/>(no rules yet)"]

            Subnet1 --- Subnet2
            Subnet2 --- Subnet3
            Firewall ---|placed in subnet 1, no traffic routed| Subnet1
        end

        subgraph DeviceTrust["Device check only. No app behind it"]
            direction LR
            VerifiedAccess["Verified Access<br/>(no app endpoint)"]
            TrustProvider["Device trust check<br/>(Jamf)"]
        end

        VerifiedAccess ---|attached| TrustProvider
    end
```

The three subnets share one private network. The firewall endpoint is only in subnet 1, and nothing routes traffic to it. Verified Access is attached to the Jamf device check and has no app endpoint.

Redraw the picture at the top with Graphviz installed: `pip install diagrams`, then `python docs/diagram.py`.

## What the code creates

| Piece | Where | What is configured |
| --- | --- | --- |
| VPC | `modules/zero-trust` | CIDR `10.0.0.0/16` by default. DNS hostnames and DNS support are enabled. Terraform defines no internet gateway, NAT gateway, security group, network ACL, or route table. A new VPC still receives AWS's default security group, default network ACL, and main route table, whose only route is the local VPC route. |
| Private subnets | `modules/zero-trust` | Three subnets from `cidrsubnet(vpc_cidr, 4, n)` for `n` = 1, 2, 3. With the default CIDR those are `10.0.16.0/20`, `10.0.32.0/20`, and `10.0.48.0/20`. Availability zones are `data.aws_availability_zones.available.names[0..2]`. That data source sets neither `state` nor `opt-in-status`, so the names are the first three the API returns, and an enabled Local Zone can be one of them. |
| Verified Access | `modules/zero-trust` | One instance, one device trust provider (`device_trust_provider_type = jamf`, policy reference `device-trust`), and the attachment between them. No endpoint, group, or access policy. |
| Network Firewall | `modules/zero-trust` | One firewall. Its only subnet mapping is the first private subnet. The policy sets stateless default and fragment default to `aws:forward_to_sfe`. No stateless or stateful rule group, and no logging. No route table sends traffic to the endpoint. |
| GuardDuty | root `main.tf` | One detector, `enable = true`, `finding_publishing_frequency = SIX_HOURS`. `SIX_HOURS` is how often GuardDuty republishes an existing finding. It is the standalone-account default. Protection plans (S3, EKS, malware, RDS, Lambda, runtime monitoring) are not set, so they stay at the CreateDetector API default. |
| Security Hub CSPM | root `main.tf` | `aws_securityhub_account` with `enable_default_standards = false` and `auto_enable_controls = true`. One standards subscription, NIST SP 800-53 Rev. 5, ARN `arn:${partition}:securityhub:${region}::standards/nist-800-53/v/5.0.0`. CIS and AWS Foundational Security Best Practices are not subscribed. New controls that AWS adds to the enabled standard are turned on automatically. |
| State bucket | `bootstrap/` | Separate stack, local state. Versioning is enabled. Default encryption is SSE-KMS with a customer-managed key (rotation enabled, 30-day deletion window, alias `alias/zero-trust-terraform-state`) and an S3 Bucket Key. Public access block sets `block_public_acls`, `block_public_policy`, `ignore_public_acls`, and `restrict_public_buckets`. The bucket policy has one statement, `DenyInsecureTransport`, which denies `s3:*` when `aws:SecureTransport` is false. No object lock, lifecycle, or replication. |

## NIST SP 800-53 Rev. 5

Support means the resource is a relevant piece of the control. It does not mean the control is met.

| Component | Controls | Support in this lab |
| --- | --- | --- |
| VPC and private subnets | SC-7 Boundary Protection | Private subnets with no internet gateway keep the lab off the public internet. Terraform defines no security groups or network ACLs. AWS's default network ACL allows all inbound and outbound traffic, and the default security group allows traffic from itself, so SC-7 is only partly addressed. |
| Network Firewall | SC-7 Boundary Protection, AC-4 Information Flow Enforcement | The firewall is the enforcement point those controls call for. This policy only forwards stateless traffic to the stateful engine. With no rule groups and no routes into the endpoint, traffic is not inspected and AC-4 is not enforced. |
| Verified Access and the Jamf device trust provider | IA-3 Device Identification and Authentication | The Jamf provider is attached, so the instance has a device-identity source. AC-17 Remote Access is the control Verified Access is built for, and this lab has no endpoint or access policy, so it does not provide remote access. |
| GuardDuty detector | SI-4 System Monitoring, SI-4(2) Automated Tools and Mechanisms for Real-Time Analysis, SI-4(4) Inbound and Outbound Communications Traffic | The detector is continuous, automated analysis. Foundational sources that ship with a detector include VPC Flow Logs and DNS logs, which is the SI-4(4) link. No notification channel or response runbook is defined. |
| Security Hub CSPM, NIST SP 800-53 Rev. 5 subscription | CA-2 Control Assessments, CA-7 Continuous Monitoring | The subscription enables AWS's automated checks for a subset of Rev. 5. Requirements that need a manual method are outside those checks. The subscription is not an assessment plan and not an authorization package. |

## CISA Zero Trust Maturity Model alignment

[CISA Zero Trust Maturity Model Version 2.0](https://www.cisa.gov/sites/default/files/2023-04/zero_trust_maturity_model_v2_508.pdf) (April 2023) describes five pillars: Identity, Devices, Networks, Applications and Workloads, and Data. This table maps those pillars to what this repo deploys. Status is `implemented`, `partial`, or `not yet`. Those words are not the model's maturity stages. The stages in the document are Traditional, Initial, Advanced, and Optimal, and this lab does not claim one. Visibility and Analytics, Automation and Orchestration, and Governance are cross-cutting capabilities in the model. This table does not score them.

| Pillar | What this repo deploys | Status |
| --- | --- | --- |
| Identity | The Verified Access instance has no user-identity trust provider. The only trust provider is the Jamf device provider, counted under Devices. There is no identity store. IAM Identity Center is out of scope. | not yet |
| Devices | One Jamf device trust provider is attached to the Verified Access instance (`trust_provider_type = device`, `device_trust_provider_type = jamf`, policy reference `device-trust`). No endpoint or access policy uses that signal to allow or deny access. | partial |
| Networks | Three private subnets, and Terraform defines no internet gateway. The Network Firewall has a baseline policy: stateless default and fragment default are `aws:forward_to_sfe`. No rule group, no logging, and no route into the endpoint, so the firewall does not inspect traffic. | partial |
| Applications and Workloads | No application or workload is defined. Verified Access has no endpoint, group, or access policy, so it does not give remote users access to a private application. GuardDuty and Security Hub CSPM monitor the account. They are not application access controls. | not yet |
| Data | No data inventory, categorization, or application data store. `bootstrap/` creates a state bucket with SSE-KMS (customer-managed key), public access blocked, and non-TLS requests denied. The main backend uses that key when `kms_key_id` is set. Those controls apply to state objects only. | partial |

## Out of scope

- **IAM Identity Center.** Standing up Identity Center is an organization-level action. The AWS provider has no portable resource that creates the Identity Center instance in a standalone account. A Verified Access user trust provider of type `iam-identity-center` also fails apply unless Identity Center is already enabled, so this lab leaves it out.
- Interface VPC endpoints (PrivateLink).
- Verified Access endpoints, groups, and Cedar policies.
- Network Firewall rule groups, firewall logging, and routes that would send subnet traffic through the firewall.
- GuardDuty protection-plan configuration, and any Security Hub standard other than NIST SP 800-53 Rev. 5.
- Multi-account administration, a delegated administrator, or aggregation across Regions.

## Layout

```
.
├── main.tf                      # provider, network module, GuardDuty, Security Hub
├── variables.tf
├── outputs.tf
├── versions.tf                  # Terraform >= 1.10, AWS provider ~> 6.0
├── backend.tf                   # partial S3 backend: encrypt and use_lockfile
├── backend.hcl.example          # bucket, region, and KMS key ARN
├── terraform.tfvars.example
├── bootstrap/                   # state bucket and KMS key; local state
├── modules/zero-trust/          # VPC, subnets, Verified Access, Network Firewall
├── docs/
│   ├── architecture.png         # picture at the top of this file
│   ├── diagram.py               # redraws that picture
│   └── icons/                   # Verified Access icon used by diagram.py
├── LICENSE                      # MIT, Copyright (c) 2026 Marlon Garcia
└── README.md
```

## Outputs

| Name | Meaning |
| --- | --- |
| `vpc_id` | VPC ID |
| `verified_access_instance_id` | Verified Access instance ID |
| `guardduty_detector_id` | GuardDuty detector ID in the provider Region |
| `securityhub_nist_subscription_arn` | Subscription ARN for NIST SP 800-53 Rev. 5 |

`bootstrap/` outputs `bucket_name`, `bucket_region`, `kms_key_arn`, and `kms_alias_arn`. The two-step init copies the first three into `backend.hcl`.
