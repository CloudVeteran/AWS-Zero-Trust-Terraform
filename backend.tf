terraform {
  backend "s3" {
    # bucket, region, and kms_key_id are account-specific.
    # Copy backend.hcl.example to backend.hcl and pass it at init:
    #   terraform init -backend-config=backend.hcl
    key          = "zero-trust/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }
}
