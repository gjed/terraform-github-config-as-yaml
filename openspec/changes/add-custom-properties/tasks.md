## 1. YAML Config Loading (yaml-config.tf)

- [ ] 1.1 Add `custom_property_config_path` local and `custom_property_files` fileset (optional directory pattern matching `membership_config_path`)
- [ ] 1.2 Add `custom_property_configs_by_file` map for per-file loading (duplicate detection)
- [ ] 1.3 Add `duplicate_custom_property_keys` local and `check "duplicate_custom_property_keys"` block
- [ ] 1.4 Add `custom_properties_config` merged map of all property definitions
- [ ] 1.5 Add subscription tier gating locals: `custom_properties_supported` (`team`/`enterprise` + `is_organization`), `effective_custom_properties`, `skipped_custom_property_names`

## 2. Custom Property Value Merging (yaml-config.tf)

- [ ] 2.1 Add `merged_custom_property_values` local that collects `custom_property_values:` from groups (in order) and merges with repo-level values (repo overrides group, matching `merged_teams` pattern)
- [ ] 2.2 Add `effective_custom_property_values` local that returns empty maps when `custom_properties_supported` is false
- [ ] 2.3 Add the `custom_property_values` key to the `repositories` local block, passing effective values to each repo

## 3. Normalize Values for Provider (yaml-config.tf)

- [ ] 3.1 Add normalization logic that wraps scalar values in a single-element list and passes list values through for `multi_select` types (lookup property type from `custom_properties_config`)

## 4. Organization-Level Resources (main.tf)

- [ ] 4.1 Add `github_organization_custom_properties` resource with `for_each = local.effective_custom_properties` mapping YAML fields to resource arguments (`property_name`, `value_type`, `required`, `description`, `default_value`, `allowed_values`, `values_editable_by`)
- [ ] 4.2 Add `depends_on = [github_organization_custom_properties.this]` to the `module "repositories"` block

## 5. Repository-Level Resources (modules/repository/)

- [ ] 5.1 Add `custom_property_values` variable to `modules/repository/variables.tf` (type: `map(list(string))`, default: `{}`)
- [ ] 5.2 Add `github_repository_custom_property` resource in `modules/repository/main.tf` with `for_each` over `var.custom_property_values`, setting `repository`, `property_name`, `property_type`, and `property_value`

## 6. Module Interface (main.tf)

- [ ] 6.1 Pass `custom_property_values = each.value.custom_property_values` to the `module "repositories"` block

## 7. Outputs (outputs.tf)

- [ ] 7.1 Add `skipped_custom_properties` output listing property names skipped due to tier/account type
- [ ] 7.2 Add `managed_custom_properties` output listing property names that are actively managed

## 8. Template YAML Config

- [ ] 8.1 Create `config/custom-property/` directory with a commented example `.yml` file showing all property types (string, single_select, multi_select, true_false)
- [ ] 8.2 Add commented `custom_property_values:` examples in the template group and repository YAML files

## 9. Validation Script (scripts/validate-config.py)

- [ ] 9.1 Add custom property definition loading and schema validation (value_type enum, allowed_values only on select types)
- [ ] 9.2 Add validation that `custom_property_values:` references exist in property definitions
- [ ] 9.3 Add validation that select-type values are in the `allowed_values` list
- [ ] 9.4 Add validation that required properties have values for all repos (warning level, not blocking)
- [ ] 9.5 Add tier-awareness: skip property validations when subscription doesn't support them (with info message)

## 10. Documentation

- [ ] 10.1 Add "Managing custom properties" section to AGENTS.md with YAML examples, tier requirements, and inheritance explanation
- [ ] 10.2 Update README.md features list to include custom properties

## 11. Verification

- [ ] 11.1 Run `terraform fmt` on all modified `.tf` files
- [ ] 11.2 Run `terraform validate` to confirm syntax
- [ ] 11.3 Run `pre-commit run --all-files` to confirm all hooks pass
- [ ] 11.4 Run `terraform plan` (with example config) to verify resource creation and dependency ordering
