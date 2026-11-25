terraform {
  required_version = ">= 1.0"

  required_providers {
    github = {
      source  = "integrations/github"
      version = ">= 6.12.0"
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

  topics = var.topics

  auto_init          = var.auto_init
  gitignore_template = var.gitignore_template
  license_template   = var.license_template

  # Archive repositories instead of deleting them on destroy. Defaults to true
  # as a safety net: if a repository leaves Terraform's view (removed from
  # config or via `terraform state rm`), the GitHub provider archives it via
  # the API rather than permanently deleting it. Only the e2e test fixture
  # overrides this to false so its throwaway repos are hard-deleted on teardown.
  # prevent_destroy is intentionally NOT set: it must be a literal and would
  # deadlock normal for_each-based repo removal.
  archive_on_destroy = var.archive_on_destroy

  lifecycle {
    # auto_init: write-only, only meaningful at creation.
    # template: the provider's Read always repopulates this from the live
    # repository's TemplateRepository field, but the schema exposes no way
    # to set it in config (there is no `template` variable on this module),
    # so any repo created from a template shows a permanent, no-op removal
    # diff. GitHub's API has no endpoint to change the template a repo was
    # created from, and the provider's Update never touches this field, so
    # ignoring it here is safe.
    ignore_changes = [auto_init, template]
  }
}

# Manage Dependabot vulnerability alerts via the dedicated resource.
resource "github_repository_vulnerability_alerts" "this" {
  repository = github_repository.this.name
  enabled    = var.vulnerability_alerts
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

        dynamic "required_reviewers" {
          # coalesce guards against an explicit `required_reviewers: null`, which
          # bypasses the optional() default.
          for_each = coalesce(try(pull_request.value.parameters.required_reviewers, null), [])
          content {
            reviewer {
              # A conditional, not coalesce(): coalesce evaluates every argument and
              # indexing team_ids with a null slug would fail.
              id = (required_reviewers.value.reviewer.id != null
                ? required_reviewers.value.reviewer.id
              : tonumber(var.team_ids[required_reviewers.value.reviewer.slug]))
              type = coalesce(required_reviewers.value.reviewer.type, "Team")
            }
            file_patterns     = required_reviewers.value.file_patterns
            minimum_approvals = required_reviewers.value.minimum_approvals
          }
        }
      }
    }

    # Required status checks rule
    dynamic "required_status_checks" {
      for_each = [for rule in each.value.rules : rule if rule.type == "required_status_checks"]
      content {
        dynamic "required_check" {
          # coalesce guards against `required_checks:` written with no value in
          # YAML, which decodes to null and cannot be used in for_each.
          for_each = coalesce(lookup(required_status_checks.value.parameters, "required_checks", []), [])
          content {
            context        = required_check.value.context
            integration_id = lookup(required_check.value, "integration_id", null)
          }
        }
        strict_required_status_checks_policy = lookup(required_status_checks.value.parameters, "strict_required_status_checks_policy", false)
        do_not_enforce_on_create             = coalesce(lookup(required_status_checks.value.parameters, "do_not_enforce_on_create", false), false)
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

# Manage repository Actions secrets
# Values are resolved from env:VAR_NAME at the root module; a missing reference fails the plan.
resource "github_actions_secret" "this" {
  for_each = var.secrets.actions

  repository  = github_repository.this.name
  secret_name = each.key
  value       = each.value.value

  lifecycle {
    precondition {
      condition     = can(regex("^[A-Z_][A-Z0-9_]*$", each.key)) && !can(regex("^GITHUB_", each.key))
      error_message = "Repository Actions secret name '${each.key}' is invalid: names must match ^[A-Z_][A-Z0-9_]*$ and must not start with GITHUB_."
    }
    precondition {
      condition     = nonsensitive(each.value.value != null)
      error_message = "Repository Actions secret '${each.key}': ${each.value.source} is not resolvable. Secret values must be env:VAR_NAME references with VAR_NAME set in secret_values."
    }
  }
}

# Manage repository Actions variables (plaintext values)
resource "github_actions_variable" "this" {
  for_each = var.variables.actions

  repository    = github_repository.this.name
  variable_name = each.key
  value         = each.value.value

  lifecycle {
    precondition {
      condition     = can(regex("^[A-Z_][A-Z0-9_]*$", each.key)) && !can(regex("^GITHUB_", each.key))
      error_message = "Repository Actions variable name '${each.key}' is invalid: names must match ^[A-Z_][A-Z0-9_]*$ and must not start with GITHUB_."
    }
    precondition {
      condition     = each.value.value != null
      error_message = "Repository Actions variable '${each.key}' has no value. Define a value in the group or repository config."
    }
  }
}

# Manage repository Dependabot secrets
resource "github_dependabot_secret" "this" {
  for_each = var.secrets.dependabot

  repository  = github_repository.this.name
  secret_name = each.key
  value       = each.value.value

  lifecycle {
    precondition {
      condition     = can(regex("^[A-Z_][A-Z0-9_]*$", each.key)) && !can(regex("^GITHUB_", each.key))
      error_message = "Repository Dependabot secret name '${each.key}' is invalid: names must match ^[A-Z_][A-Z0-9_]*$ and must not start with GITHUB_."
    }
    precondition {
      condition     = nonsensitive(each.value.value != null)
      error_message = "Repository Dependabot secret '${each.key}': ${each.value.source} is not resolvable. Secret values must be env:VAR_NAME references with VAR_NAME set in secret_values."
    }
  }
}

# Manage repository environments with their protection rules
# Free-tier private repositories are filtered out at the yaml-config layer
# (see skipped_environments output).
resource "github_repository_environment" "this" {
  for_each = var.environments

  repository          = github_repository.this.name
  environment         = each.key
  wait_timer          = each.value.wait_timer
  can_admins_bypass   = each.value.can_admins_bypass
  prevent_self_review = each.value.prevent_self_review

  # Users are given by login and teams by slug; both are resolved to IDs by the root module.
  dynamic "reviewers" {
    for_each = length(each.value.reviewers.users) + length(each.value.reviewers.teams) > 0 ? [each.value.reviewers] : []
    content {
      users = [for login in reviewers.value.users : tonumber(var.user_ids[login])]
      teams = [for slug in reviewers.value.teams : tonumber(var.team_ids[slug])]
    }
  }

  # GitHub rejects a policy with both flags false, so the block is only emitted when one is set.
  dynamic "deployment_branch_policy" {
    for_each = each.value.deployment_branch_policy.protected_branches || each.value.deployment_branch_policy.custom_branch_policies ? [each.value.deployment_branch_policy] : []
    content {
      protected_branches     = deployment_branch_policy.value.protected_branches
      custom_branch_policies = deployment_branch_policy.value.custom_branch_policies
    }
  }

  # GitHub rejects reviewers that cannot access the repository, so access grants come first.
  depends_on = [github_team_repository.this, github_repository_collaborator.this]

  lifecycle {
    precondition {
      condition     = !(each.value.deployment_branch_policy.protected_branches && each.value.deployment_branch_policy.custom_branch_policies)
      error_message = "Environment '${each.key}': deployment_branch_policy.protected_branches and deployment_branch_policy.custom_branch_policies are mutually exclusive. Set only one of them."
    }
    precondition {
      condition = each.value.deployment_branch_policy.custom_branch_policies || (
        length(each.value.deployment_branch_policy.branch_patterns) + length(each.value.deployment_branch_policy.tag_patterns) == 0
      )
      error_message = "Environment '${each.key}': branch_patterns and tag_patterns require deployment_branch_policy.custom_branch_policies: true."
    }
    precondition {
      condition = !each.value.deployment_branch_policy.custom_branch_policies || (
        length(each.value.deployment_branch_policy.branch_patterns) + length(each.value.deployment_branch_policy.tag_patterns) > 0
      )
      error_message = "Environment '${each.key}': deployment_branch_policy.custom_branch_policies: true needs at least one entry in branch_patterns or tag_patterns, otherwise no branch or tag can deploy."
    }
    precondition {
      condition     = each.value.wait_timer >= 0 && each.value.wait_timer <= 43200
      error_message = "Environment '${each.key}': wait_timer must be between 0 and 43200 minutes."
    }
  }
}

locals {
  # One deployment policy per branch or tag pattern, keyed <environment>/branch:<pattern> or
  # <environment>/tag:<pattern>. Only environments with custom_branch_policies get policies.
  environment_deployment_policies = merge([
    for env, e in var.environments : merge(
      { for p in e.deployment_branch_policy.branch_patterns : "${env}/branch:${p}" => { environment = env, branch_pattern = p, tag_pattern = null } },
      { for p in e.deployment_branch_policy.tag_patterns : "${env}/tag:${p}" => { environment = env, branch_pattern = null, tag_pattern = p } },
    ) if e.deployment_branch_policy.custom_branch_policies
  ]...)

  # Keys only: the maps hold no secret values, so for_each stays plan-time known. Values are
  # read from var.environments inside the resources.
  environment_secret_keys = {
    for item in flatten([
      for env, e in var.environments : [for name in keys(e.secrets) : { key = "${env}/${name}", environment = env, name = name }]
    ]) : item.key => item
  }

  environment_variable_keys = {
    for item in flatten([
      for env, e in var.environments : [for name in keys(e.variables) : { key = "${env}/${name}", environment = env, name = name }]
    ]) : item.key => item
  }
}

resource "github_repository_environment_deployment_policy" "this" {
  for_each = local.environment_deployment_policies

  repository     = github_repository.this.name
  environment    = github_repository_environment.this[each.value.environment].environment
  branch_pattern = each.value.branch_pattern
  tag_pattern    = each.value.tag_pattern
}

# Manage environment secrets
# Values are resolved from env:VAR_NAME at the root module; a missing reference fails the plan.
resource "github_actions_environment_secret" "this" {
  for_each = local.environment_secret_keys

  repository  = github_repository.this.name
  environment = github_repository_environment.this[each.value.environment].environment
  secret_name = each.value.name
  value       = var.environments[each.value.environment].secrets[each.value.name].value

  lifecycle {
    precondition {
      condition     = can(regex("^[A-Z_][A-Z0-9_]*$", each.value.name)) && !can(regex("^GITHUB_", each.value.name))
      error_message = "Environment '${each.value.environment}' secret name '${each.value.name}' is invalid: names must match ^[A-Z_][A-Z0-9_]*$ and must not start with GITHUB_."
    }
    precondition {
      condition     = nonsensitive(var.environments[each.value.environment].secrets[each.value.name].value != null)
      error_message = "Environment '${each.value.environment}' secret '${each.value.name}': ${var.environments[each.value.environment].secrets[each.value.name].source} is not resolvable. Secret values must be env:VAR_NAME references with VAR_NAME set in secret_values."
    }
  }
}

# Manage environment variables (plaintext values)
resource "github_actions_environment_variable" "this" {
  for_each = local.environment_variable_keys

  repository    = github_repository.this.name
  environment   = github_repository_environment.this[each.value.environment].environment
  variable_name = each.value.name
  value         = var.environments[each.value.environment].variables[each.value.name].value

  lifecycle {
    precondition {
      condition     = can(regex("^[A-Z_][A-Z0-9_]*$", each.value.name)) && !can(regex("^GITHUB_", each.value.name))
      error_message = "Environment '${each.value.environment}' variable name '${each.value.name}' is invalid: names must match ^[A-Z_][A-Z0-9_]*$ and must not start with GITHUB_."
    }
    precondition {
      condition     = var.environments[each.value.environment].variables[each.value.name].value != null
      error_message = "Environment '${each.value.environment}' variable '${each.value.name}' has no value. Define a value in the group or repository config."
    }
  }
}

# Manage custom property values
# The property definitions are created by the root module before the repositories (depends_on).
# Everything is skipped at the yaml-config layer when the tier or account type does not support
# custom properties (see skipped_custom_properties output).
resource "github_repository_custom_property" "this" {
  for_each = var.custom_property_values

  repository     = github_repository.this.name
  property_name  = each.key
  property_type  = coalesce(each.value.value_type, "string")
  property_value = toset(coalesce(each.value.values, []))

  lifecycle {
    precondition {
      condition     = each.value.value_type != null
      error_message = "Repository '${var.name}' sets custom property '${each.key}', which is not defined in config/custom-property/."
    }
    precondition {
      condition     = each.value.values != null
      error_message = "Repository '${var.name}' custom property '${each.key}': the value must be a string, number, boolean, or a list of those."
    }
    precondition {
      condition     = try(length(each.value.values) > 0, false)
      error_message = "Repository '${var.name}' custom property '${each.key}': at least one value is required."
    }
    precondition {
      condition     = each.value.value_type == "multi_select" || try(length(each.value.values) <= 1, true)
      error_message = "Repository '${var.name}' custom property '${each.key}' is of type ${coalesce(each.value.value_type, "unknown")} and takes exactly one value; only multi_select properties take a list."
    }
    precondition {
      condition     = !try(contains(["single_select", "multi_select"], each.value.value_type), false) || alltrue([for v in coalesce(each.value.values, []) : contains(each.value.allowed_values, v)])
      error_message = "Repository '${var.name}' custom property '${each.key}': ${join(", ", [for v in coalesce(each.value.values, []) : "'${v}'" if !contains(each.value.allowed_values, v)])} not in the allowed values (${join(", ", each.value.allowed_values)})."
    }
    precondition {
      condition     = each.value.value_type != "true_false" || alltrue([for v in coalesce(each.value.values, []) : contains(["true", "false"], v)])
      error_message = "Repository '${var.name}' custom property '${each.key}' is of type true_false and takes true or false."
    }
  }
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
