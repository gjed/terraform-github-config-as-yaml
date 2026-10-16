# Plan-only regression tests for config/secret/*.yml and repo-level secrets/variables.
# mock_provider keeps every run offline: no GITHUB_TOKEN and no organization are needed.
# Run from the repository root with: terraform init -backend=false && terraform test

mock_provider "github" {}

run "valid_config_plans" {
  command = plan

  variables {
    config_path = "./tests/terraform/fixtures/secrets-valid/config"
    secret_values = {
      DEPLOY_TOKEN      = "placeholder" # pragma: allowlist secret
      API_TOKEN         = "placeholder" # pragma: allowlist secret
      REGISTRY_PASSWORD = "placeholder" # pragma: allowlist secret
    }
  }

  # Organization level: three types, merged per type across config/secret/*.yml files.
  assert {
    condition     = length(github_actions_organization_secret.this) == 2
    error_message = "Expected 2 organization Actions secrets, got ${length(github_actions_organization_secret.this)}."
  }

  assert {
    condition     = github_actions_organization_secret.this["ORG_SELECTED_TOKEN"].visibility == "selected"
    error_message = "ORG_SELECTED_TOKEN should have visibility selected."
  }

  assert {
    condition     = length(github_actions_organization_variable.this) == 2
    error_message = "Expected 2 organization Actions variables, got ${length(github_actions_organization_variable.this)}."
  }

  # zz-overrides.yml is sorted last, so its value wins over org-variables.yml.
  assert {
    condition     = github_actions_organization_variable.this["ORG_VARIABLE"].value == "overridden"
    error_message = "ORG_VARIABLE should take the value from the last config/secret file that defines it."
  }

  # An explicitly empty selected_repositories list is valid (fix A keeps null only when omitted).
  assert {
    condition     = github_actions_organization_variable.this["ORG_EMPTY_LIST_VARIABLE"].visibility == "selected"
    error_message = "ORG_EMPTY_LIST_VARIABLE should be planned with visibility selected and an empty list."
  }

  assert {
    condition     = github_dependabot_organization_secret.this["ORG_DEPENDABOT_SECRET"].visibility == "private"
    error_message = "ORG_DEPENDABOT_SECRET should be planned as an organization Dependabot secret."
  }

  # Repo level: group secrets are inherited and repo entries are added. Names come from the
  # module's secret_names and variable_names outputs, because module resources are not
  # addressable from test assertions. Repo variable values are not output, so the group/repo
  # value override (LOG_LEVEL) is not asserted here.
  assert {
    condition     = alltrue([for k in ["GROUP_SECRET", "REPO_SECRET"] : contains(module.repositories["fixture-app"].secret_names.actions, k)])
    error_message = "fixture-app should get GROUP_SECRET from the oss group and REPO_SECRET from its own entry."
  }

  assert {
    condition     = module.repositories["fixture-lib"].secret_names.actions == ["GROUP_SECRET"]
    error_message = "fixture-lib should only get GROUP_SECRET from the oss group."
  }

  assert {
    condition     = contains(module.repositories["fixture-app"].secret_names.dependabot, "GROUP_DEPENDABOT_SECRET")
    error_message = "fixture-app should inherit GROUP_DEPENDABOT_SECRET from the oss group."
  }

  assert {
    condition     = contains(module.repositories["fixture-app"].variable_names, "LOG_LEVEL") && contains(module.repositories["fixture-lib"].variable_names, "LOG_LEVEL")
    error_message = "Both fixture repositories should inherit LOG_LEVEL from the base group."
  }
}

# Precondition failures are plan errors, so expect_failures lists the org resources that must fail.
# Every other value is supplied, so the only failures in this plan are the expected ones.
#
# Limitation: repo-level preconditions (repository secrets, dependabot secrets, variables in
# modules/repository) are not covered. Module resources are not addressable from test
# expect_failures in this setup; validate-config.py covers the same name and value rules
# for those entries.
run "invalid_config_fails_preconditions" {
  command = plan

  variables {
    config_path = "./tests/terraform/fixtures/secrets-invalid/config"
    secret_values = {
      DEPLOY_TOKEN = "placeholder" # pragma: allowlist secret
    }
  }

  expect_failures = [
    github_actions_organization_secret.this["lowercase_secret"],
    github_actions_organization_secret.this["GITHUB_RESERVED"],
    github_actions_organization_secret.this["MISSING_ENV_SECRET"],
    github_actions_organization_secret.this["BAD_VISIBILITY_SECRET"],
    github_actions_organization_secret.this["UNKNOWN_REPO_SECRET"],
    github_actions_organization_secret.this["NO_LIST_SECRET"],
    github_actions_organization_variable.this["lowercase_variable"],
    github_actions_organization_variable.this["NO_LIST_VARIABLE"],
    github_dependabot_organization_secret.this["MISSING_ENV_DEPENDABOT"],
  ]
}
