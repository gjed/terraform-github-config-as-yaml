terraform {
  required_version = ">= 1.0"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
}

resource "github_repository" "this" {
  name         = var.name
  description  = var.description
  visibility   = var.visibility
  homepage_url = var.homepage_url

  has_wiki        = var.has_wiki
  has_issues      = var.has_issues
  has_projects    = var.has_projects
  has_discussions = var.has_discussions

  allow_merge_commit          = var.allow_merge_commit
  allow_squash_merge          = var.allow_squash_merge
  allow_rebase_merge          = var.allow_rebase_merge
  allow_auto_merge            = var.allow_auto_merge
  allow_update_branch         = var.allow_update_branch
  delete_branch_on_merge      = var.delete_branch_on_merge
  web_commit_signoff_required = var.web_commit_signoff_required
  vulnerability_alerts        = var.vulnerability_alerts

  topics = var.topics

  auto_init          = var.auto_init
  gitignore_template = var.gitignore_template
  license_template   = var.license_template

  lifecycle {
    prevent_destroy = false
    ignore_changes  = [auto_init]
  }
}

# Manage team access to the repository
resource "github_team_repository" "this" {
  for_each = var.teams

  team_id    = each.key
  repository = github_repository.this.name
  permission = each.value
}

# Manage individual collaborator access to the repository
resource "github_repository_collaborator" "this" {
  for_each = var.collaborators

  username   = each.key
  repository = github_repository.this.name
  permission = each.value
}

# Manage repository rulesets
resource "github_repository_ruleset" "this" {
  for_each = var.rulesets

  name        = each.key
  repository  = github_repository.this.name
  target      = each.value.target
  enforcement = each.value.enforcement

  conditions {
    ref_name {
      include = each.value.conditions.ref_name.include
      exclude = each.value.conditions.ref_name.exclude
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

    # Required deployments rule
    dynamic "required_deployments" {
      for_each = [for rule in each.value.rules : rule if rule.type == "required_deployments"]
      content {
        required_deployment_environments = required_deployments.value.parameters.required_deployment_environments
      }
    }

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

# Manage GitHub Actions permissions for the repository
# Only created when actions configuration is provided
# Note: default_workflow_permissions and can_approve_pull_request_reviews are
# organization-level settings managed via github_actions_organization_workflow_permissions
resource "github_actions_repository_permissions" "this" {
  count = var.actions != null ? 1 : 0

  repository = github_repository.this.name
  enabled    = var.actions.enabled

  # Which actions are allowed to run
  allowed_actions = var.actions.allowed_actions

  # Configuration for "selected" allowed_actions policy
  dynamic "allowed_actions_config" {
    for_each = var.actions.allowed_actions == "selected" && var.actions.allowed_actions_config != null ? [var.actions.allowed_actions_config] : []
    content {
      github_owned_allowed = allowed_actions_config.value.github_owned_allowed
      verified_allowed     = allowed_actions_config.value.verified_allowed
      patterns_allowed     = allowed_actions_config.value.patterns_allowed
    }
  }
}

# Manage repository webhooks
# Note: Secrets are resolved at the yaml-config layer before being passed to this module
resource "github_repository_webhook" "this" {
  for_each = var.webhooks

  repository = github_repository.this.name

  configuration {
    url          = each.value.url
    content_type = each.value.content_type
    secret       = each.value.secret
    insecure_ssl = each.value.insecure_ssl
  }

  events = each.value.events
  active = each.value.active
}

# Manage traditional branch protection rules
# Keyed by protection name (e.g. "main-protection") - renaming requires a state move
resource "github_branch_protection" "this" {
  for_each = var.branch_protections

  repository_id = github_repository.this.node_id
  pattern       = each.value.pattern

  # Top-level boolean controls
  enforce_admins                  = each.value.enforce_admins
  allows_deletions                = each.value.allows_deletions
  allows_force_pushes             = each.value.allows_force_pushes
  lock_branch                     = each.value.lock_branch
  require_conversation_resolution = each.value.require_conversation_resolution
  require_signed_commits          = each.value.require_signed_commits
  required_linear_history         = each.value.required_linear_history

  # Required pull request reviews - only when the sub-object is present
  dynamic "required_pull_request_reviews" {
    for_each = each.value.required_pull_request_reviews != null ? [each.value.required_pull_request_reviews] : []
    content {
      required_approving_review_count = required_pull_request_reviews.value.required_approving_review_count
      dismiss_stale_reviews           = required_pull_request_reviews.value.dismiss_stale_reviews
      require_code_owner_reviews      = required_pull_request_reviews.value.require_code_owner_reviews
      require_last_push_approval      = required_pull_request_reviews.value.require_last_push_approval
      restrict_dismissals             = required_pull_request_reviews.value.restrict_dismissals

      # Actor values are passed through as-is. Use the provider's format in YAML:
      #   users: "/username"  teams: "orgname/teamslug"  apps: node_id
      dismissal_restrictions = required_pull_request_reviews.value.dismissal_restrictions != null ? concat(
        required_pull_request_reviews.value.dismissal_restrictions.users,
        required_pull_request_reviews.value.dismissal_restrictions.teams,
        required_pull_request_reviews.value.dismissal_restrictions.apps,
      ) : []

      pull_request_bypassers = required_pull_request_reviews.value.pull_request_bypassers != null ? concat(
        required_pull_request_reviews.value.pull_request_bypassers.users,
        required_pull_request_reviews.value.pull_request_bypassers.teams,
        required_pull_request_reviews.value.pull_request_bypassers.apps,
      ) : []
    }
  }

  # Required status checks - only when the sub-object is present
  dynamic "required_status_checks" {
    for_each = each.value.required_status_checks != null ? [each.value.required_status_checks] : []
    content {
      strict   = required_status_checks.value.strict
      contexts = required_status_checks.value.contexts
    }
  }

  # Restrict pushes - only when the sub-object is present
  dynamic "restrict_pushes" {
    for_each = each.value.restrict_pushes != null ? [each.value.restrict_pushes] : []
    content {
      blocks_creations = restrict_pushes.value.blocks_creations

      # Actor values are passed through as-is. Use the provider's format in YAML:
      #   users: "/username"  teams: "orgname/teamslug"  apps: node_id
      push_allowances = restrict_pushes.value.push_allowances != null ? concat(
        restrict_pushes.value.push_allowances.users,
        restrict_pushes.value.push_allowances.teams,
        restrict_pushes.value.push_allowances.apps,
      ) : []
    }
  }
}
