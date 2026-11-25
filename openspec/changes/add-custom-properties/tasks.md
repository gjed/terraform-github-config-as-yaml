## 1. YAML config loading (yaml-config.tf)

- [ ] 1.1 Load `config/custom-property/*.yml` (optional directory, comment-only files tolerated) into per-file maps and
  a merged `custom_properties_config`
- [ ] 1.2 Detect duplicate property names across files (`duplicate_custom_property_keys`) with a
  `check "duplicate_custom_property_keys"` block and an entry in the `duplicate_key_warnings` output
- [ ] 1.3 Normalize each definition to a uniform shape (`description`, `value_type`, `required`, `default_value`,
  `allowed_values`, `values_editable_by`) tolerant of nulls and YAML booleans
- [ ] 1.4 Add tier gating locals: `custom_properties_supported` (`team`/`enterprise` and `is_organization`),
  `effective_custom_properties`, `skipped_custom_property_names`

## 2. Value merging and normalization (yaml-config.tf)

- [ ] 2.1 Merge `custom_property_values` from groups (in order) and the repository (repository wins by property name)
- [ ] 2.2 Normalize scalars to one-element lists and pass lists through; attach the definition's `value_type` and
  `allowed_values`; filter everything out when `custom_properties_supported` is false
- [ ] 2.3 Add `custom_property_values` to the `repositories` local block
- [ ] 2.4 Compute the repositories missing each required property that has no default

## 3. Resources and wiring

- [ ] 3.1 Add `custom-properties.tf` with `github_organization_custom_properties` (`for_each` over
  `effective_custom_properties`) and preconditions for `value_type`, `allowed_values`, `default_value`,
  `values_editable_by` and required properties
- [ ] 3.2 Add the `custom_property_values` variable to `modules/repository/variables.tf`
- [ ] 3.3 Add `github_repository_custom_property` to `modules/repository/main.tf` with preconditions for undefined
  properties, value shape and allowed values, and expose the assigned names in `modules/repository/outputs.tf`
- [ ] 3.4 Pass `custom_property_values` to `module "repositories"` and add `depends_on` on the definitions
- [ ] 3.5 Add `managed_custom_properties` and `skipped_custom_properties` outputs to `outputs.tf`

## 4. Validation (scripts/validate-config.py)

- [ ] 4.1 Add `custom_property_values` to `VALID_GROUP_KEYS` and load `config/custom-property/` (`set_config_dir`
  included)
- [ ] 4.2 Validate definitions: `value_type`, `allowed_values` vs type, `default_value`, `values_editable_by`, unknown keys
- [ ] 4.3 Validate assignments in groups and repositories: undefined names, value shape, allowed values, `true_false`
- [ ] 4.4 Validate required properties against each repository's effective values and the property default
- [ ] 4.5 Warn when definitions or assignments exist on an unsupported tier or account type

## 5. Tests

- [ ] 5.1 Add `tests/test_validate_custom_properties.py`
- [ ] 5.2 Add `tests/custom_properties.tftest.hcl` with fixtures: merge precedence, scalar-to-list normalization, tier skip
  with output, duplicate detection, invalid value and required-missing failures
- [ ] 5.3 Extend the e2e fixture (`tests/e2e/config`, `tests/e2e/main.tf`) and `tests/verify_e2e.py`

## 6. Documentation and examples

- [ ] 6.1 Add `config/custom-property/examples.yml` (commented, all four types) and commented
  `custom_property_values:` examples in the template group and repository YAML
- [ ] 6.2 Add "Managing custom properties" to AGENTS.md (definitions, assignments, tier requirements, inheritance,
  required and default semantics)
- [ ] 6.3 Add custom properties to the README.md feature list and configuration reference

## 7. Verification

- [ ] 7.1 `terraform fmt -check -recursive`, `terraform validate` and `terraform test` pass
- [ ] 7.2 `pytest tests/`, `python scripts/validate-config.py` and `openspec validate --all` pass
- [ ] 7.3 `pre-commit run --all-files` and the markdown lint pass
- [ ] 7.4 Archive the change and fix the Purpose heading spacing in the new specs
