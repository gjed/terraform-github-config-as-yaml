# Organization-level custom property definitions.
# Definitions come from config/custom-property/*.yml (see yaml-config.tf).
# Only created for organizations; for a personal account they are skipped and listed in the
# skipped_custom_properties output.
#
# Values are assigned per repository by modules/repository, which depends on these definitions
# (depends_on on module.repositories in main.tf).

resource "github_organization_custom_properties" "this" {
  for_each = local.effective_custom_properties

  property_name      = each.key
  value_type         = each.value.value_type
  description        = each.value.description
  required           = each.value.required
  default_value      = each.value.default_value
  allowed_values     = each.value.allowed_values
  values_editable_by = each.value.values_editable_by

  lifecycle {
    precondition {
      condition     = try(contains(["string", "single_select", "multi_select", "true_false"], each.value.value_type), false)
      error_message = "Custom property '${each.key}' value_type must be one of: string, single_select, multi_select, true_false."
    }
    precondition {
      condition = (
        !try(contains(["single_select", "multi_select"], each.value.value_type), false) ||
        try(length(each.value.allowed_values) > 0, false)
      )
      error_message = "Custom property '${each.key}' is a select type and needs a non-empty allowed_values list."
    }
    precondition {
      condition = (
        try(contains(["single_select", "multi_select"], each.value.value_type), false) ||
        try(length(each.value.allowed_values) == 0, true)
      )
      error_message = "Custom property '${each.key}': allowed_values only applies to single_select and multi_select properties."
    }
    precondition {
      condition = each.value.default_value == null || (
        try(contains(["single_select", "multi_select"], each.value.value_type), false)
        ? try(contains(each.value.allowed_values, each.value.default_value), false)
        : (each.value.value_type == "true_false" ? contains(["true", "false"], each.value.default_value) : true)
      )
      error_message = "Custom property '${each.key}': default_value must be one of allowed_values for select types and true or false for true_false."
    }
    precondition {
      condition     = each.value.values_editable_by == null || try(contains(["org_actors", "org_and_repo_actors"], each.value.values_editable_by), false)
      error_message = "Custom property '${each.key}': values_editable_by must be org_actors or org_and_repo_actors."
    }
    precondition {
      condition     = length(local.custom_property_repos_missing_required[each.key]) == 0
      error_message = "Custom property '${each.key}' is required and has no default_value, but these repositories do not set it: ${join(", ", local.custom_property_repos_missing_required[each.key])}. Set it in a group or repository custom_property_values, or add a default_value."
    }
  }
}
