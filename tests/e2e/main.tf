terraform {
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
}

provider "github" {
  owner = var.github_org
}

module "github_org" {
  source = "../../"

  config_path = "${path.module}/config"

  repository_partitions = ["partitioned"]

  webhook_secrets = {
    E2E_WEBHOOK_SECRET = var.webhook_secret
  }

  membership_management_enabled = var.membership_management_enabled
}
