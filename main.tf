# GitHub Organization Terraform Module
# YAML configuration is loaded from the directory specified by var.config_path.
#
# Consumers must configure the GitHub provider in their own root module, e.g.:
#
#   provider "github" {
#     owner = "your-org-name"
#   }
#
# See examples/consumer/ for a complete consumer setup.

terraform {
  required_version = ">= 1.0"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
}

# Manage all repositories using YAML configuration
module "repositories" {
  source = "./modules/repository"

  for_each = local.repositories

  name         = each.value.name
  description  = each.value.description
  homepage_url = each.value.homepage_url
  visibility   = each.value.visibility

  has_wiki        = each.value.has_wiki
  has_issues      = each.value.has_issues
  has_projects    = each.value.has_projects
  has_discussions = each.value.has_discussions

  allow_merge_commit          = each.value.allow_merge_commit
  allow_squash_merge          = each.value.allow_squash_merge
  allow_rebase_merge          = each.value.allow_rebase_merge
  allow_auto_merge            = each.value.allow_auto_merge
  allow_update_branch         = each.value.allow_update_branch
  delete_branch_on_merge      = each.value.delete_branch_on_merge
  web_commit_signoff_required = each.value.web_commit_signoff_required
  vulnerability_alerts        = each.value.vulnerability_alerts

  topics        = each.value.topics
  teams         = each.value.teams
  collaborators = each.value.collaborators

  license_template = each.value.license_template

  # Apply rulesets based on repository groups
  rulesets = each.value.rulesets

  # Apply Actions permissions configuration
  actions = each.value.actions

  # Apply webhooks from groups and repo-specific definitions
  webhooks = each.value.webhooks

}

# Organization membership management
# Only managed when membership_management_enabled = true AND target is an organization
# WARNING: Removing a username from config/membership/ will remove them from the org on apply
# WARNING: Do NOT use alongside SCIM/IdP provisioning — they will conflict
resource "github_membership" "this" {
  for_each = local.effective_membership

  username = each.key
  role     = each.value
}

# Organization-level Actions permissions
# Only created when actions configuration is specified in config.yml
resource "github_actions_organization_permissions" "this" {
  count = local.org_actions_config != null ? 1 : 0

  # Which repositories can use Actions: all, none, selected
  enabled_repositories = try(local.org_actions_config.enabled_repositories, "all")

  # Which actions are allowed: all, local_only, selected
  allowed_actions = try(local.org_actions_config.allowed_actions, "all")

  # Configuration for "selected" allowed_actions policy
  dynamic "allowed_actions_config" {
    for_each = try(local.org_actions_config.allowed_actions, "all") == "selected" ? [1] : []
    content {
      github_owned_allowed = try(local.org_actions_config.allowed_actions_config.github_owned_allowed, true)
      verified_allowed     = try(local.org_actions_config.allowed_actions_config.verified_allowed, true)
      patterns_allowed     = try(local.org_actions_config.allowed_actions_config.patterns_allowed, [])
    }
  }
}

# Organization-level workflow permissions (GITHUB_TOKEN defaults)
# Only created when actions configuration is specified in config.yml
resource "github_actions_organization_workflow_permissions" "this" {
  count = local.org_actions_config != null ? 1 : 0

  organization_slug = local.github_org

  # Default GITHUB_TOKEN permissions: read or write
  # Secure default: read (principle of least privilege)
  default_workflow_permissions = try(local.org_actions_config.default_workflow_permissions, "read")

  # Whether Actions can approve pull request reviews
  # Secure default: false
  can_approve_pull_request_reviews = try(local.org_actions_config.can_approve_pull_request_reviews, false)
}

# Manage GitHub Teams - Tier 0 (root teams, no parent)
# Only created for organizations (teams are not available for personal accounts)
module "teams_root" {
  source = "./modules/team"

  for_each = local.is_organization ? local.tier_0_teams : {}

  name        = each.value.name
  description = each.value.description
  privacy     = each.value.privacy
  members     = each.value.members
  maintainers = each.value.maintainers

  review_request_delegation = each.value.review_request_delegation
}

# Manage GitHub Teams - Tier 1 (children of root teams)
module "teams_level_1" {
  source = "./modules/team"

  for_each = local.is_organization ? local.tier_1_teams : {}

  name           = each.value.name
  description    = each.value.description
  privacy        = each.value.privacy
  parent_team_id = module.teams_root[each.value.parent_slug].team_id
  members        = each.value.members
  maintainers    = each.value.maintainers

  review_request_delegation = each.value.review_request_delegation
}

# Manage GitHub Teams - Tier 2 (grandchildren, max depth)
module "teams_level_2" {
  source = "./modules/team"

  for_each = local.is_organization ? local.tier_2_teams : {}

  name           = each.value.name
  description    = each.value.description
  privacy        = each.value.privacy
  parent_team_id = module.teams_level_1[each.value.parent_slug].team_id
  members        = each.value.members
  maintainers    = each.value.maintainers

  review_request_delegation = each.value.review_request_delegation
}
