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

  secret_values = {
    E2E_SECRET_VALUE = var.e2e_secret_value
  }

  membership_management_enabled = var.membership_management_enabled

  # Hard-delete throwaway e2e repos on teardown so `make destroy` leaves no
  # orphans and the next apply does not collide with archived repo names.
  archive_on_destroy = false
}
