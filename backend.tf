terraform {
  backend "s3" {
    # Replace this with an S3 bucket you own before a real init.
    bucket       = "terraform-state-bucket-mag0508"
    key          = "zero-trust/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
    encrypt      = true
  }
}
