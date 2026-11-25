# Plan-only regression tests for repository environments.
# mock_provider keeps every run offline: no GITHUB_TOKEN and no organization are needed.
# Run from the repository root with: terraform init -backend=false && terraform test

mock_provider "github" {
  # Reviewer IDs reach the module through tonumber(), so mocked lookups must return numeric strings.
  mock_data "github_user" {
    defaults = {
      id = "1001"
    }
  }
  mock_data "github_team" {
    defaults = {
      id = "2002"
    }
  }
  mock_resource "github_team" {
    defaults = {
      id = "3003"
    }
  }
}

run "merge_precedence" {
  command = plan

  variables {
    config_path = "./tests/terraform/fixtures/environments-valid/config"
    secret_values = {
      DEPLOY_TOKEN = "placeholder" # pragma: allowlist secret
      API_TOKEN    = "placeholder" # pragma: allowlist secret
    }
  }

  # The later group (hardened) replaces production from base, and the replacement is whole:
  # base's reviewer team and GROUP_SECRET are not inherited.
  assert {
    condition     = local.repositories["env-app"].environments["production"].wait_timer == 60
    error_message = "env-app production should take wait_timer 60 from the later group."
  }

  assert {
    condition     = length(local.repositories["env-app"].environments["production"].secrets) == 0
    error_message = "env-app production must not inherit GROUP_SECRET from the replaced group definition."
  }

  assert {
    condition     = join(",", local.repositories["env-app"].environments["production"].reviewers.teams) == "security-team"
    error_message = "env-app production should keep only the reviewers of the later group."
  }

  # A repository entry replaces the group entry of the same name.
  assert {
    condition     = local.repositories["env-lib"].environments["production"].wait_timer == 0 && length(local.repositories["env-lib"].environments["production"].secrets) == 0
    error_message = "env-lib production should be the repository definition, not merged with the base group."
  }

  # Distinct environments from groups and the repository are all kept; names only are output.
  assert {
    condition     = join(",", sort(keys(module.repositories["env-app"].environments))) == "production,qa,staging"
    error_message = "env-app should get staging (base), production (hardened) and qa (repository)."
  }

  assert {
    condition     = join(",", module.repositories["env-app"].environments["qa"].secrets) == "QA_SECRET" && join(",", module.repositories["env-app"].environments["qa"].variables) == "RETRIES"
    error_message = "env-app qa should list its secret and variable names."
  }

  assert {
    condition     = join(",", module.repositories["env-lib"].environments["staging"].variables) == "LOG_LEVEL"
    error_message = "env-lib should inherit staging from the base group."
  }

  assert {
    condition     = length(module.repositories["env-plain"].environments) == 0 && !contains(keys(output.repository_environments), "env-plain")
    error_message = "env-plain has no environments and must not appear in repository_environments."
  }

  # Explicit nulls in YAML must not break the module's defaults.
  assert {
    condition     = join(",", sort(keys(module.repositories["env-nulls"].environments))) == "bare,empty"
    error_message = "env-nulls should plan both environments despite null properties."
  }

  assert {
    condition     = output.skipped_environments == null
    error_message = "Nothing is skipped on the team tier."
  }

  # Reviewer logins and external team slugs are looked up; managed teams are not.
  assert {
    condition     = contains(keys(data.github_user.environment_reviewers), "octocat")
    error_message = "The user reviewer octocat should be resolved with a github_user lookup."
  }

  assert {
    condition     = contains(keys(data.github_team.reviewers), "platform") && !contains(keys(data.github_team.reviewers), "security-team")
    error_message = "platform should be looked up, but the managed security-team must resolve from its resource."
  }
}

# Free tier: environments of private repositories are skipped as a whole, and reported.
run "free_tier_skips_private_repositories" {
  command = plan

  variables {
    config_path = "./tests/terraform/fixtures/environments-free/config"
    secret_values = {
      DEPLOY_TOKEN = "placeholder" # pragma: allowlist secret
    }
  }

  assert {
    condition     = length(module.repositories["private-app"].environments) == 0
    error_message = "The private repository must get no environments on the free tier."
  }

  assert {
    condition     = join(",", keys(module.repositories["public-app"].environments)) == "production"
    error_message = "The public repository keeps its environments on the free tier."
  }

  assert {
    condition     = output.skipped_environments != null && join(",", output.skipped_environments.repos) == "private-app" && join(",", output.skipped_environments.environments["private-app"]) == "production" && output.skipped_environments.tier == "free"
    error_message = "skipped_environments should list private-app and its production environment."
  }

  assert {
    condition     = join(",", keys(output.repository_environments)) == "public-app"
    error_message = "repository_environments should only list the public repository."
  }
}

# The preconditions live on module resources, which are not addressable from the root module
# in expect_failures, so the module is planned directly.
run "mutually_exclusive_branch_policies_fail" {
  command = plan

  module {
    source = "./modules/repository"
  }

  variables {
    name        = "fixture"
    description = "fixture"
    environments = {
      production = {
        deployment_branch_policy = {
          protected_branches     = true
          custom_branch_policies = true
        }
      }
    }
  }

  expect_failures = [
    github_repository_environment.this["production"],
  ]
}

run "patterns_without_custom_policies_fail" {
  command = plan

  module {
    source = "./modules/repository"
  }

  variables {
    name        = "fixture"
    description = "fixture"
    environments = {
      production = {
        deployment_branch_policy = {
          protected_branches = true
          branch_patterns    = ["main"]
        }
      }
    }
  }

  expect_failures = [
    github_repository_environment.this["production"],
  ]
}

run "wait_timer_out_of_range_fails" {
  command = plan

  module {
    source = "./modules/repository"
  }

  variables {
    name        = "fixture"
    description = "fixture"
    environments = {
      production = {
        wait_timer = 43201
      }
    }
  }

  expect_failures = [
    github_repository_environment.this["production"],
  ]
}

run "unresolvable_secret_and_bad_names_fail" {
  command = plan

  module {
    source = "./modules/repository"
  }

  variables {
    name        = "fixture"
    description = "fixture"
    environments = {
      production = {
        secrets = {
          MISSING_REF = { value = null, source = "env:MISSING" } # pragma: allowlist secret
          lowercase   = { value = "x", source = "env:OK" }       # pragma: allowlist secret
        }
        variables = {
          GITHUB_RESERVED = { value = "x" }
        }
      }
    }
  }

  expect_failures = [
    github_actions_environment_secret.this["production/MISSING_REF"],
    github_actions_environment_secret.this["production/lowercase"],
    github_actions_environment_variable.this["production/GITHUB_RESERVED"],
  ]
}

run "custom_policies_create_one_resource_per_pattern" {
  command = plan

  module {
    source = "./modules/repository"
  }

  variables {
    name        = "fixture"
    description = "fixture"
    environments = {
      production = {
        deployment_branch_policy = {
          custom_branch_policies = true
          branch_patterns        = ["main", "release/*"]
          tag_patterns           = ["v*"]
        }
      }
    }
  }

  assert {
    condition     = join(",", sort(keys(github_repository_environment_deployment_policy.this))) == "production/branch:main,production/branch:release/*,production/tag:v*"
    error_message = "Expected one deployment policy per branch and tag pattern."
  }

  assert {
    condition     = github_repository_environment_deployment_policy.this["production/tag:v*"].tag_pattern == "v*"
    error_message = "Tag patterns must use tag_pattern."
  }
}
