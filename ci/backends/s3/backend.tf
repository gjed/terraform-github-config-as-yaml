# S3 backend (AWS). Copy to backend.tf in your consumer repository.
#
# The state holds secret values (webhook and Actions secrets, repository settings), so keep the bucket
# private, encrypted and versioned, and limit who can read it.
#
# Credentials: the AWS SDK default chain. In CI prefer short-lived credentials from OIDC
# (aws-actions/configure-aws-credentials with a role) over long-lived access keys.

terraform {
  required_version = ">= 1.0"

  backend "s3" {
    bucket  = "your-terraform-state-bucket" # REPLACE
    key     = "github-org/terraform.tfstate"
    region  = "us-east-1" # REPLACE
    encrypt = true

    # State locking. use_lockfile needs Terraform 1.10 or later; older versions
    # use a DynamoDB table instead: dynamodb_table = "terraform-state-lock"
    use_lockfile = true
  }
}
