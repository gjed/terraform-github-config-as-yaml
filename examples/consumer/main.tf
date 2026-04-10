# Consumer entrypoint — minimal setup to use the github-as-yaml module.
#
# Prerequisites:
#   export GITHUB_TOKEN="ghp_..."
#
# Then run:
#   terraform init && terraform plan && terraform apply

terraform {
  required_version = ">= 1.0"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
}

# Configure the GitHub provider.
# owner must be set here because provider configuration runs before module
# evaluation, so the org name from config.yml is not available at this stage.
provider "github" {
  owner = "your-org-name" # Replace with your GitHub organization name

  # Optional: rate limiting for large organizations.
  # GitHub API limit: 5000 requests/hour for authenticated requests.
  # Increase these when managing 100+ repositories.
  # read_delay_ms  = 0
  # write_delay_ms = 100
}

module "github_org" {
  # Use the Terraform Registry for version-constrained, reproducible builds.
  source  = "gjed/config-as-yaml/github"
  version = "~> 1.0"

  # Path to the config directory relative to this file.
  # Must be a static string — computed values are not supported.
  config_path = "${path.root}/config"

  # Optional: scope the plan to specific repository partitions (subdirectories
  # under config/repository/). Useful for large organisations that exceed GitHub
  # API rate limits on a full plan.
  #
  # Example directory layout:
  #   config/repository/
  #   ├── common.yml          # Always loaded (top-level, not a partition)
  #   ├── infra/              # Partition "infra"
  #   │   └── services.yml
  #   └── product/            # Partition "product"
  #       └── apps.yml
  #
  # Load only the "infra" partition (common.yml is still always loaded):
  #   repository_partitions = ["infra"]
  #
  # Default (empty list) loads all partitions — identical to pre-partitioning
  # behaviour. No migration needed for flat config/repository/ layouts.
  #
  # ⚠️  WARNING: Narrowing the partition list causes repositories outside the
  # selected partitions to disappear from Terraform's view, resulting in a
  # planned destroy for their resources. Always review the plan carefully before
  # applying when changing repository_partitions. See docs/scaling.md for details.
  #
  # repository_partitions = []  # default: all partitions

  # Optional: pass webhook secrets via environment variables or a secrets manager.
  # webhook_secrets = {
  #   MY_WEBHOOK_SECRET = var.my_webhook_secret
  # }
}
