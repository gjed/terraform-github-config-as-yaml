## ADDED Requirements

### Requirement: Define custom properties via YAML

The system SHALL load custom property definitions from `config/custom-property/*.yml` files. Each top-level key in the
YAML represents one custom property. The YAML structure for each property SHALL support:

- `description` (string, optional): human-readable description
- `value_type` (string, required): one of `string`, `single_select`, `multi_select`, `true_false`
- `required` (boolean, optional, default: `false`): whether repos must have a value
- `default_value` (string, optional): default value for the property
- `allowed_values` (list of strings, optional): valid values for `single_select` and `multi_select` types
- `values_editable_by` (string, optional): `org_actors` (default) or `org_and_repo_actors`

#### Scenario: Load property definitions from YAML files

- **WHEN** `config/custom-property/` contains one or more `.yml` files with property definitions
- **THEN** the system SHALL parse each file and create a `github_organization_custom_properties` resource for each
  top-level key

#### Scenario: Multiple YAML files merged

- **WHEN** property definitions are split across multiple files (e.g., `compliance.yml`, `metadata.yml`)
- **THEN** the system SHALL merge all files into a single property definitions map (same pattern as rulesets, webhooks)

#### Scenario: Missing directory is not an error

- **WHEN** the `config/custom-property/` directory does not exist
- **THEN** the system SHALL proceed with an empty set of custom property definitions (no resources created, no errors)

#### Scenario: Comment-only file is not an error

- **WHEN** a `config/custom-property/*.yml` file contains only comments and blank lines
- **THEN** the system SHALL treat it as an empty definition set and create no resources from it

### Requirement: Detect duplicate property names across files

The system SHALL detect when the same property name appears as a top-level key in multiple
`config/custom-property/*.yml` files and surface a warning via a Terraform `check` block and the
`duplicate_key_warnings` output.

#### Scenario: Duplicate property name across files

- **WHEN** property `environment` is defined in both `compliance.yml` and `metadata.yml`
- **THEN** the system SHALL emit a check warning listing the duplicate key and the files it appears in
- **AND** the `duplicate_key_warnings` output SHALL list the key under custom properties

### Requirement: Subscription tier gating for property definitions

The system SHALL only create `github_organization_custom_properties` resources when the subscription tier is `team` or
`enterprise` AND `is_organization` is `true`. On all other configurations, property definition resources SHALL be
skipped.

#### Scenario: Free tier skips property definitions

- **WHEN** `subscription` is `free` and custom property definitions exist in YAML
- **THEN** no `github_organization_custom_properties` resources SHALL be created

#### Scenario: Personal account skips property definitions

- **WHEN** `is_organization` is `false` and custom property definitions exist in YAML
- **THEN** no `github_organization_custom_properties` resources SHALL be created

#### Scenario: Team tier creates property definitions

- **WHEN** `subscription` is `team` and `is_organization` is `true`
- **THEN** `github_organization_custom_properties` resources SHALL be created for each defined property

### Requirement: Output managed and skipped custom properties

The system SHALL expose a `managed_custom_properties` output listing the names of the created property definitions, and
a `skipped_custom_properties` output listing the names of definitions that were skipped due to subscription tier or
account type. Both outputs SHALL contain names only.

#### Scenario: Skipped properties listed in output

- **WHEN** custom properties are defined but skipped due to tier/account type
- **THEN** the `skipped_custom_properties` output SHALL list the names of all skipped property definitions
- **AND** the `managed_custom_properties` output SHALL be an empty list

#### Scenario: No skip warning when properties are created

- **WHEN** custom properties are defined and the subscription tier supports them
- **THEN** the `skipped_custom_properties` output SHALL be an empty list
- **AND** the `managed_custom_properties` output SHALL list the defined property names

### Requirement: Validate property definitions

The system SHALL reject invalid property definitions, both in `validate-config.py` and as `terraform plan` failures
from preconditions on the `github_organization_custom_properties` resource.

- `value_type` SHALL be one of `string`, `single_select`, `multi_select`, `true_false`
- `allowed_values` SHALL be required (non-empty) for `single_select` and `multi_select` and SHALL NOT be set for other
  types
- `default_value`, when set, SHALL be one of `allowed_values` for select types and `true` or `false` for `true_false`
- `values_editable_by`, when set, SHALL be `org_actors` or `org_and_repo_actors`

#### Scenario: Invalid value type

- **WHEN** a property defines `value_type: number`
- **THEN** the validation script SHALL report an error naming the property and the allowed value types
- **AND** `terraform plan` SHALL fail on that property's resource

#### Scenario: Default outside the allowed values

- **WHEN** a `single_select` property has `allowed_values: [development, staging]` and `default_value: production`
- **THEN** the validation script SHALL report an error that the default is not one of the allowed values
- **AND** `terraform plan` SHALL fail on that property's resource

#### Scenario: Allowed values on a non-select type

- **WHEN** a `string` property defines `allowed_values`
- **THEN** the validation script SHALL report an error that `allowed_values` only applies to select types

### Requirement: Warn when custom properties are skipped by the tier

The validation script SHALL warn when custom property definitions or `custom_property_values:` assignments exist and the
configuration is not an organization on the `team` or `enterprise` subscription, because Terraform skips them.

#### Scenario: Definitions on the free tier

- **WHEN** `subscription` is `free` and `config/custom-property/` defines properties
- **THEN** the validation script SHALL emit a warning that the properties require a Team or Enterprise plan and will be
  skipped
