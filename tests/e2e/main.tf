terraform {
  required_version = ">= 1.5"

  required_providers {
    github = {
      source  = "integrations/github"
      version = ">= 6.12.0, < 7.0.0"
    }
  }
}

provider "github" {
  owner = var.github_org
}

module "github_org" {
  source = "../../"

  config_path = "${path.module}/config"

  webhook_secrets = {
    E2E_WEBHOOK_SECRET = var.webhook_secret
  }

  membership_management_enabled = var.membership_management_enabled
}
