# Organization-level Actions secrets, Actions variables, and Dependabot secrets.
# Definitions come from config/secret/*.yml (see yaml-config.tf).
# Only created for organizations; personal accounts skip all of these resources.
#
# selected_repositories names are resolved to repository IDs from module.repositories.
# Names that are not managed by this module fail the plan in a precondition.

resource "github_actions_organization_secret" "this" {
  for_each = local.is_organization ? local.org_actions_secrets : {}

  secret_name = each.key
  visibility  = each.value.visibility
  value       = each.value.value

  selected_repository_ids = each.value.visibility == "selected" ? [
    for r in each.value.selected_repositories : module.repositories[r].repo_id
    if contains(keys(local.repos_yaml), r)
  ] : null

  lifecycle {
    precondition {
      condition     = can(regex("^[A-Z_][A-Z0-9_]*$", each.key)) && !can(regex("^GITHUB_", each.key))
      error_message = "Organization Actions secret name '${each.key}' is invalid: names must match ^[A-Z_][A-Z0-9_]*$ and must not start with GITHUB_."
    }
    precondition {
      condition     = nonsensitive(each.value.value != null)
      error_message = "Organization Actions secret '${each.key}': ${each.value.source} is not resolvable. Secret values must be env:VAR_NAME references with VAR_NAME set in secret_values."
    }
    precondition {
      condition     = try(contains(["all", "private", "selected"], each.value.visibility), false)
      error_message = "Organization Actions secret '${each.key}' visibility must be one of: all, private, selected."
    }
    precondition {
      condition     = each.value.visibility != "selected" || alltrue([for r in each.value.selected_repositories : contains(keys(local.repos_yaml), r)])
      error_message = "Organization Actions secret '${each.key}' selects repositories not defined in config/repository/: ${join(", ", [for r in each.value.selected_repositories : r if !contains(keys(local.repos_yaml), r)])}."
    }
  }
}

resource "github_actions_organization_variable" "this" {
  for_each = local.is_organization ? local.org_actions_variables : {}

  variable_name = each.key
  value         = each.value.value
  visibility    = each.value.visibility

  selected_repository_ids = each.value.visibility == "selected" ? [
    for r in each.value.selected_repositories : module.repositories[r].repo_id
    if contains(keys(local.repos_yaml), r)
  ] : null

  lifecycle {
    precondition {
      condition     = can(regex("^[A-Z_][A-Z0-9_]*$", each.key)) && !can(regex("^GITHUB_", each.key))
      error_message = "Organization Actions variable name '${each.key}' is invalid: names must match ^[A-Z_][A-Z0-9_]*$ and must not start with GITHUB_."
    }
    precondition {
      condition     = each.value.value != null
      error_message = "Organization Actions variable '${each.key}' has no value. Define a value in config/secret/."
    }
    precondition {
      condition     = try(contains(["all", "private", "selected"], each.value.visibility), false)
      error_message = "Organization Actions variable '${each.key}' visibility must be one of: all, private, selected."
    }
    precondition {
      condition     = each.value.visibility != "selected" || alltrue([for r in each.value.selected_repositories : contains(keys(local.repos_yaml), r)])
      error_message = "Organization Actions variable '${each.key}' selects repositories not defined in config/repository/: ${join(", ", [for r in each.value.selected_repositories : r if !contains(keys(local.repos_yaml), r)])}."
    }
  }
}

resource "github_dependabot_organization_secret" "this" {
  for_each = local.is_organization ? local.org_dependabot_secrets : {}

  secret_name = each.key
  visibility  = each.value.visibility
  value       = each.value.value

  selected_repository_ids = each.value.visibility == "selected" ? [
    for r in each.value.selected_repositories : module.repositories[r].repo_id
    if contains(keys(local.repos_yaml), r)
  ] : null

  lifecycle {
    precondition {
      condition     = can(regex("^[A-Z_][A-Z0-9_]*$", each.key)) && !can(regex("^GITHUB_", each.key))
      error_message = "Organization Dependabot secret name '${each.key}' is invalid: names must match ^[A-Z_][A-Z0-9_]*$ and must not start with GITHUB_."
    }
    precondition {
      condition     = nonsensitive(each.value.value != null)
      error_message = "Organization Dependabot secret '${each.key}': ${each.value.source} is not resolvable. Secret values must be env:VAR_NAME references with VAR_NAME set in secret_values."
    }
    precondition {
      condition     = try(contains(["all", "private", "selected"], each.value.visibility), false)
      error_message = "Organization Dependabot secret '${each.key}' visibility must be one of: all, private, selected."
    }
    precondition {
      condition     = each.value.visibility != "selected" || alltrue([for r in each.value.selected_repositories : contains(keys(local.repos_yaml), r)])
      error_message = "Organization Dependabot secret '${each.key}' selects repositories not defined in config/repository/: ${join(", ", [for r in each.value.selected_repositories : r if !contains(keys(local.repos_yaml), r)])}."
    }
  }
}
