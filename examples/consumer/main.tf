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
      version = ">= 6.12.0, < 7.0.0"
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
  # under config/repository/). This is a STATIC STATE-SHARDING mechanism: each
  # non-empty partition list MUST be paired with a dedicated Terraform state
  # (its own root module and backend), set once at bootstrap and never varied
  # dynamically between plans in that state.
  #
  # Example directory layout:
  #   config/repository/
  #   ├── common.yml          # Always loaded (top-level, not a partition)
  #   ├── infra/              # Partition "infra"
  #   │   └── services.yml
  #   └── product/            # Partition "product"
  #       └── apps.yml
  #
  # For single-state consumers (common case), omit repository_partitions or set
  # it to []. For multi-state sharding, create separate root modules:
  #   infra-root/main.tf:   repository_partitions = ["infra"]
  #   product-root/main.tf: repository_partitions = ["product"]
  # Each gets its own Terraform backend (separate state).
  #
  # ⚠️  CRITICAL: Never narrow repository_partitions dynamically against a shared
  # state. Narrowing causes repositories outside the new selection to vanish from
  # the for_each key set while remaining in state, triggering destroy plans.
  # This is unsupported and will destroy every repository outside the partition.
  # See docs/scaling.md "Repository Partitioning" for the per-partition-state contract.
  #
  # repository_partitions = []  # default: all partitions (recommended for single-state)

  # Optional: pass webhook secrets via environment variables or a secrets manager.
  # Used for both repository-level and organization-level webhooks that use
  # the env:VAR_NAME secret pattern in config/webhook/.
  # webhook_secrets = {
  #   MY_WEBHOOK_SECRET       = var.my_webhook_secret
  #   ORG_WEBHOOK_SECRET      = var.org_webhook_secret
  # }

  # Optional: enable organization membership management via config/membership/.
  #
  # WARNING: When enabled, removing a username from config/membership/ will remove that person
  # from the GitHub organization on the next terraform apply, revoking all private repo access
  # and destroying private forks. Always run terraform plan and review before applying.
  #
  # WARNING: Do NOT enable alongside SCIM/IdP provisioning (Okta, Azure AD, SCIM) — they conflict.
  #
  # membership_management_enabled = true
  #
  # Organization webhooks are configured in config/config.yml under org_webhooks:.
  # They fire for events across ALL repositories in the organization.
  # Example: org_webhooks: [audit-logger, ci-notifier]
}
