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

  # Apply branch protection rules from groups and repo-specific definitions
  branch_protections = each.value.branch_protections

}

# Organization membership management
# Only managed when membership_management_enabled = true AND target is an organization
# WARNING: Removing a username from config/membership/ will remove them from the org on apply
# WARNING: Do NOT use alongside SCIM/IdP provisioning — they will conflict
resource "github_membership" "this" {
  for_each = local.effective_membership

  username = each.key
  role     = each.value

  lifecycle {
    precondition {
      condition     = contains(["member", "admin"], each.value)
      error_message = "Invalid role '${each.value}' for member '${each.key}'. Valid roles: member, admin."
    }
  }
}

# Organization-level rulesets
# Applied globally across repositories based on repository_name conditions
# Requires team or enterprise subscription (skipped on free/pro - see skipped_org_rulesets output)
resource "github_organization_ruleset" "this" {
  for_each = local.effective_org_rulesets

  name        = each.key
  target      = each.value.target
  enforcement = each.value.enforcement

  conditions {
    ref_name {
      include = each.value.conditions.ref_name.include
      exclude = each.value.conditions.ref_name.exclude
    }

    # repository_name is required by the GitHub provider (AtLeastOneOf constraint).
    # When omitted from YAML config, defaults to include all repositories.
    repository_name {
      include = lookup(lookup(lookup(each.value, "conditions", {}), "repository_name", {}), "include", ["*"])
      exclude = lookup(lookup(lookup(each.value, "conditions", {}), "repository_name", {}), "exclude", [])
    }
  }

  # Bypass actors - allow specific users/teams/apps to bypass rules
  dynamic "bypass_actors" {
    for_each = lookup(each.value, "bypass_actors", null) != null ? each.value.bypass_actors : []
    content {
      actor_id    = bypass_actors.value.actor_id
      actor_type  = bypass_actors.value.actor_type
      bypass_mode = lookup(bypass_actors.value, "bypass_mode", "always")
    }
  }

  # Rules - single block containing all rule types
  rules {
    # Branch name pattern rule
    dynamic "branch_name_pattern" {
      for_each = [for rule in each.value.rules : rule if rule.type == "branch_name_pattern"]
      content {
        operator = lookup(branch_name_pattern.value.parameters, "operator", "starts_with")
        pattern  = branch_name_pattern.value.parameters.pattern
        name     = lookup(branch_name_pattern.value.parameters, "name", null)
        negate   = lookup(branch_name_pattern.value.parameters, "negate", false)
      }
    }

    # Deletion rule
    deletion = contains([for rule in each.value.rules : rule.type], "deletion") ? true : null

    # Non-fast-forward rule
    non_fast_forward = contains([for rule in each.value.rules : rule.type], "non_fast_forward") ? true : null

    # Required linear history rule
    required_linear_history = contains([for rule in each.value.rules : rule.type], "required_linear_history") ? true : null

    # Required signatures rule
    required_signatures = contains([for rule in each.value.rules : rule.type], "required_signatures") ? true : null

    # Pull request rule
    dynamic "pull_request" {
      for_each = [for rule in each.value.rules : rule if rule.type == "pull_request"]
      content {
        required_approving_review_count   = lookup(pull_request.value.parameters, "required_approving_review_count", 1)
        dismiss_stale_reviews_on_push     = lookup(pull_request.value.parameters, "dismiss_stale_reviews_on_push", false)
        require_code_owner_review         = lookup(pull_request.value.parameters, "require_code_owner_review", false)
        require_last_push_approval        = lookup(pull_request.value.parameters, "require_last_push_approval", false)
        required_review_thread_resolution = lookup(pull_request.value.parameters, "required_review_thread_resolution", false)
      }
    }

    # Required status checks rule
    dynamic "required_status_checks" {
      for_each = [for rule in each.value.rules : rule if rule.type == "required_status_checks"]
      content {
        dynamic "required_check" {
          for_each = lookup(required_status_checks.value.parameters, "required_checks", [])
          content {
            context        = required_check.value.context
            integration_id = lookup(required_check.value, "integration_id", null)
          }
        }
        strict_required_status_checks_policy = lookup(required_status_checks.value.parameters, "strict_required_status_checks_policy", false)
      }
    }

    # Creation rule
    creation = contains([for rule in each.value.rules : rule.type], "creation") ? true : null

    # Update rule
    update = contains([for rule in each.value.rules : rule.type], "update") ? true : null

    # Commit message pattern rule
    dynamic "commit_message_pattern" {
      for_each = [for rule in each.value.rules : rule if rule.type == "commit_message_pattern"]
      content {
        operator = lookup(commit_message_pattern.value.parameters, "operator", "starts_with")
        pattern  = commit_message_pattern.value.parameters.pattern
        name     = lookup(commit_message_pattern.value.parameters, "name", null)
        negate   = lookup(commit_message_pattern.value.parameters, "negate", false)
      }
    }

    # Commit author email pattern rule
    dynamic "commit_author_email_pattern" {
      for_each = [for rule in each.value.rules : rule if rule.type == "commit_author_email_pattern"]
      content {
        operator = lookup(commit_author_email_pattern.value.parameters, "operator", "starts_with")
        pattern  = commit_author_email_pattern.value.parameters.pattern
        name     = lookup(commit_author_email_pattern.value.parameters, "name", null)
        negate   = lookup(commit_author_email_pattern.value.parameters, "negate", false)
      }
    }

    # Committer email pattern rule
    dynamic "committer_email_pattern" {
      for_each = [for rule in each.value.rules : rule if rule.type == "committer_email_pattern"]
      content {
        operator = lookup(committer_email_pattern.value.parameters, "operator", "starts_with")
        pattern  = committer_email_pattern.value.parameters.pattern
        name     = lookup(committer_email_pattern.value.parameters, "name", null)
        negate   = lookup(committer_email_pattern.value.parameters, "negate", false)
      }
    }
  }
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

# Organization-level settings
# 2.1 Only created when `settings:` block is configured and is_organization = true
resource "github_organization_settings" "this" {
  count = local.org_settings_config != null ? 1 : 0

  # Profile fields
  # billing_email is required by the provider. org_settings_config is only non-null when
  # billing_email is present (enforced in yaml-config.tf and validate-config.py), so the
  # try() fallback to null here is a safety net that will never fire in practice.
  billing_email = try(local.org_settings_config.billing_email, null)
  company       = try(local.org_settings_config.company, null)
  blog          = try(local.org_settings_config.blog, null)
  email         = try(local.org_settings_config.email, null)
  location      = try(local.org_settings_config.location, null)
  description   = try(local.org_settings_config.description, null)

  # 2.2 Member privilege settings
  # Absent keys resolve to null so only explicitly configured keys are managed by Terraform.
  # Hard-coded defaults would overwrite existing org settings for keys the user did not set.
  default_repository_permission           = try(local.org_settings_config.default_repository_permission, null)
  members_can_create_repositories         = try(local.org_settings_config.members_can_create_repositories, null)
  members_can_create_public_repositories  = try(local.org_settings_config.members_can_create_public_repositories, null)
  members_can_create_private_repositories = try(local.org_settings_config.members_can_create_private_repositories, null)
  members_can_fork_private_repositories   = try(local.org_settings_config.members_can_fork_private_repositories, null)
  web_commit_signoff_required             = try(local.org_settings_config.web_commit_signoff_required, null)

  # Dependabot / dependency graph settings (available on all tiers)
  # Null for absent keys — leaves existing org settings unmanaged rather than forcing false.
  dependabot_alerts_enabled_for_new_repositories           = try(local.org_settings_config.dependabot_alerts_enabled_for_new_repositories, null)
  dependabot_security_updates_enabled_for_new_repositories = try(local.org_settings_config.dependabot_security_updates_enabled_for_new_repositories, null)
  dependency_graph_enabled_for_new_repositories            = try(local.org_settings_config.dependency_graph_enabled_for_new_repositories, null)

  # 2.3 GHAS / Enterprise-only settings
  # On non-enterprise tiers these keys are filtered out of org_settings_config in yaml-config.tf.
  # Null (not false) so absent keys are omitted entirely — no unintended disables or perpetual diffs.
  advanced_security_enabled_for_new_repositories               = try(local.org_settings_config.advanced_security_enabled_for_new_repositories, null)
  secret_scanning_enabled_for_new_repositories                 = try(local.org_settings_config.secret_scanning_enabled_for_new_repositories, null)
  secret_scanning_push_protection_enabled_for_new_repositories = try(local.org_settings_config.secret_scanning_push_protection_enabled_for_new_repositories, null)

  # 2.4 members_can_create_internal_repositories requires GitHub Enterprise
  # Filtered from org_settings_config on non-enterprise tiers; null omits it from the resource.
  members_can_create_internal_repositories = try(local.org_settings_config.members_can_create_internal_repositories, null)
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
