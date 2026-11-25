# Plan-only regression tests for organization custom properties and their repository assignments.
# mock_provider keeps every run offline: no GITHUB_TOKEN and no organization are needed.
# Run from the repository root with: terraform init -backend=false && terraform test

mock_provider "github" {}

run "merge_and_normalisation" {
  command = plan

  variables {
    config_path = "./tests/terraform/fixtures/custom-properties-valid/config"
  }

  # Definitions from every file are loaded, the comment-only file is ignored.
  assert {
    condition     = join(",", output.managed_custom_properties) == "compliance_level,environment,is_deprecated,owner,tags"
    error_message = "All five definitions across the files should be managed."
  }

  assert {
    condition     = length(output.skipped_custom_properties) == 0
    error_message = "Nothing is skipped on the team tier."
  }

  assert {
    condition     = github_organization_custom_properties.this["environment"].required && github_organization_custom_properties.this["environment"].default_value == "development" && github_organization_custom_properties.this["compliance_level"].values_editable_by == "org_and_repo_actors"
    error_message = "Definition fields should reach the resource."
  }

  # Later group replaces an earlier group's value; a repository replaces the group's value.
  assert {
    condition     = join(",", local.repositories["cp-app"].custom_property_values["environment"].values) == "production"
    error_message = "cp-app should take environment from the later group (oss)."
  }

  assert {
    condition     = join(",", local.repositories["cp-app"].custom_property_values["compliance_level"].values) == "soc2"
    error_message = "cp-app compliance_level should be overridden by the repository."
  }

  # A repository list replaces the group list instead of concatenating.
  assert {
    condition     = join(",", local.repositories["cp-app"].custom_property_values["tags"].values) == "backend,critical"
    error_message = "cp-app tags should be the repository list, not merged with the group list."
  }

  # Scalars wrap into one-element lists, booleans become strings, and the definition's type is attached.
  assert {
    condition     = join(",", local.repositories["cp-app"].custom_property_values["is_deprecated"].values) == "false" && local.repositories["cp-app"].custom_property_values["is_deprecated"].value_type == "true_false"
    error_message = "A boolean should become the one-element list [\"false\"] of a true_false property."
  }

  assert {
    condition     = local.repositories["cp-app"].custom_property_values["tags"].value_type == "multi_select" && length(local.repositories["cp-app"].custom_property_values["tags"].allowed_values) == 3
    error_message = "Assignments should carry the type and allowed values of their definition."
  }

  assert {
    condition     = join(",", module.repositories["cp-app"].custom_properties) == "compliance_level,environment,is_deprecated,owner,tags"
    error_message = "cp-app should get one assignment per property."
  }

  # Values from a single group are inherited as they are.
  assert {
    condition     = join(",", local.repositories["cp-lib"].custom_property_values["tags"].values) == "frontend" && join(",", local.repositories["cp-lib"].custom_property_values["environment"].values) == "development"
    error_message = "cp-lib should inherit the base group values."
  }

  # No value at all: the required property is satisfied by its default; null blocks are empty.
  assert {
    condition     = length(module.repositories["cp-plain"].custom_properties) == 0 && length(module.repositories["cp-nulls"].custom_properties) == 0
    error_message = "cp-plain and cp-nulls set no values and must get no assignments."
  }
}

# Free tier: definitions and assignments are skipped, and the definitions are reported.
run "free_tier_skips_with_output" {
  command = plan

  variables {
    config_path = "./tests/terraform/fixtures/custom-properties-free/config"
  }

  assert {
    condition     = length(github_organization_custom_properties.this) == 0 && length(output.managed_custom_properties) == 0
    error_message = "No definition may be created on the free tier."
  }

  assert {
    condition     = join(",", output.skipped_custom_properties) == "environment,owner"
    error_message = "skipped_custom_properties should list both definitions by name."
  }

  assert {
    condition     = length(module.repositories["free-app"].custom_properties) == 0
    error_message = "The free-app assignments must be skipped on the free tier."
  }
}

run "personal_account_skips_with_output" {
  command = plan

  variables {
    config_path = "./tests/terraform/fixtures/custom-properties-personal/config"
  }

  assert {
    condition     = length(github_organization_custom_properties.this) == 0 && join(",", output.skipped_custom_properties) == "environment"
    error_message = "A personal account on the team tier must still skip custom properties."
  }

  assert {
    condition     = length(module.repositories["personal-app"].custom_properties) == 0
    error_message = "Assignments must be skipped for a personal account."
  }
}

# A property name defined in two files raises the check and is listed in the warnings output.
run "duplicate_definitions_warn" {
  command = plan

  variables {
    config_path = "./tests/terraform/fixtures/custom-properties-duplicates/config"
  }

  assert {
    condition     = join(",", keys(output.duplicate_key_warnings.custom_properties)) == "environment"
    error_message = "duplicate_key_warnings should list the duplicated property."
  }

  # The later file wins entirely.
  assert {
    condition     = length(github_organization_custom_properties.this["environment"].allowed_values) == 2
    error_message = "The last file alphabetically should define the property."
  }

  expect_failures = [
    check.duplicate_custom_property_keys,
  ]
}

# Definition-level failures: invalid types, allowed values and defaults, and a required property
# that a repository does not set. valid_one is the only definition that plans.
run "invalid_definitions_fail_preconditions" {
  command = plan

  variables {
    config_path = "./tests/terraform/fixtures/custom-properties-invalid/config"
  }

  expect_failures = [
    github_organization_custom_properties.this["bad_type"],
    github_organization_custom_properties.this["no_allowed"],
    github_organization_custom_properties.this["allowed_on_string"],
    github_organization_custom_properties.this["bad_default"],
    github_organization_custom_properties.this["bad_bool_default"],
    github_organization_custom_properties.this["bad_editable_by"],
    github_organization_custom_properties.this["needs_value"],
  ]
}

# The assignment preconditions live on module resources, which are not addressable from the root
# module in expect_failures, so the module is planned directly.
run "multi_select_takes_a_list" {
  command = plan

  module {
    source = "./modules/repository"
  }

  variables {
    name        = "fixture"
    description = "fixture"
    custom_property_values = {
      tags   = { value_type = "multi_select", allowed_values = ["a", "b"], values = ["a", "b"] }
      owner  = { value_type = "string", values = ["anything"] }
      active = { value_type = "true_false", values = ["true"] }
    }
  }

  assert {
    condition     = join(",", sort(keys(github_repository_custom_property.this))) == "active,owner,tags"
    error_message = "Valid assignments should plan one resource per property."
  }

  assert {
    condition     = github_repository_custom_property.this["tags"].property_type == "multi_select" && length(github_repository_custom_property.this["tags"].property_value) == 2
    error_message = "The multi_select assignment should carry both values."
  }
}

run "undefined_property_fails" {
  command = plan

  module {
    source = "./modules/repository"
  }

  variables {
    name        = "fixture"
    description = "fixture"
    custom_property_values = {
      nonexistent = { values = ["x"] }
    }
  }

  expect_failures = [
    github_repository_custom_property.this["nonexistent"],
  ]
}

run "value_outside_allowed_values_fails" {
  command = plan

  module {
    source = "./modules/repository"
  }

  variables {
    name        = "fixture"
    description = "fixture"
    custom_property_values = {
      environment = { value_type = "single_select", allowed_values = ["development", "production"], values = ["testing"] }
      tags        = { value_type = "multi_select", allowed_values = ["a", "b"], values = ["a", "c"] }
    }
  }

  expect_failures = [
    github_repository_custom_property.this["environment"],
    github_repository_custom_property.this["tags"],
  ]
}

run "single_value_types_reject_lists_and_bad_booleans" {
  command = plan

  module {
    source = "./modules/repository"
  }

  variables {
    name        = "fixture"
    description = "fixture"
    custom_property_values = {
      environment = { value_type = "single_select", allowed_values = ["development", "production"], values = ["development", "production"] }
      owner       = { value_type = "string", values = ["a", "b"] }
      deprecated  = { value_type = "true_false", values = ["maybe"] }
    }
  }

  expect_failures = [
    github_repository_custom_property.this["environment"],
    github_repository_custom_property.this["owner"],
    github_repository_custom_property.this["deprecated"],
  ]
}

run "malformed_and_empty_values_fail" {
  command = plan

  module {
    source = "./modules/repository"
  }

  variables {
    name        = "fixture"
    description = "fixture"
    custom_property_values = {
      not_a_scalar = { value_type = "string" }
      empty_list   = { value_type = "multi_select", allowed_values = ["a"], values = [] }
    }
  }

  expect_failures = [
    github_repository_custom_property.this["not_a_scalar"],
    github_repository_custom_property.this["empty_list"],
  ]
}
