## ADDED Requirements

### Requirement: Define custom properties via YAML

The system SHALL load custom property definitions from `config/custom-property/*.yml` files. Each top-level key in the YAML represents one custom property. The YAML structure for each property SHALL support:

- `description` (string, optional): human-readable description
- `value_type` (string, required): one of `string`, `single_select`, `multi_select`, `true_false`
- `required` (boolean, optional, default: `false`): whether repos must have a value
- `default_value` (string, optional): default value for the property
- `allowed_values` (list of strings, optional): valid values for `single_select` and `multi_select` types
- `values_editable_by` (string, optional): `org_actors` (default) or `org_and_repo_actors`

#### Scenario: Load property definitions from YAML files

- **WHEN** `config/custom-property/` contains one or more `.yml` files with property definitions
- **THEN** the system SHALL parse each file and create a `github_organization_custom_properties` resource for each top-level key

#### Scenario: Multiple YAML files merged

- **WHEN** property definitions are split across multiple files (e.g., `compliance.yml`, `metadata.yml`)
- **THEN** the system SHALL merge all files into a single property definitions map (same pattern as rulesets, webhooks)

#### Scenario: Missing directory is not an error

- **WHEN** the `config/custom-property/` directory does not exist
- **THEN** the system SHALL proceed with an empty set of custom property definitions (no resources created, no errors)

### Requirement: Detect duplicate property names across files

The system SHALL detect when the same property name appears as a top-level key in multiple `config/custom-property/*.yml` files and surface a warning via a Terraform `check` block.

#### Scenario: Duplicate property name across files

- **WHEN** property `environment` is defined in both `compliance.yml` and `metadata.yml`
- **THEN** the system SHALL emit a check warning listing the duplicate key and the files it appears in

### Requirement: Subscription tier gating for property definitions

The system SHALL only create `github_organization_custom_properties` resources when the subscription tier is `team` or `enterprise` AND `is_organization` is `true`. On all other configurations, property definition resources SHALL be skipped.

#### Scenario: Free tier skips property definitions

- **WHEN** `subscription` is `free` and custom property definitions exist in YAML
- **THEN** no `github_organization_custom_properties` resources SHALL be created

#### Scenario: Personal account skips property definitions

- **WHEN** `is_organization` is `false` and custom property definitions exist in YAML
- **THEN** no `github_organization_custom_properties` resources SHALL be created

#### Scenario: Team tier creates property definitions

- **WHEN** `subscription` is `team` and `is_organization` is `true`
- **THEN** `github_organization_custom_properties` resources SHALL be created for each defined property

### Requirement: Output skipped custom properties warning

The system SHALL expose an output listing custom property names that were skipped due to subscription tier or account type, matching the pattern used by `skipped_org_rulesets`.

#### Scenario: Skipped properties listed in output

- **WHEN** custom properties are defined but skipped due to tier/account type
- **THEN** the `skipped_custom_properties` output SHALL list the names of all skipped property definitions

#### Scenario: No skip warning when properties are created

- **WHEN** custom properties are defined and the subscription tier supports them
- **THEN** the `skipped_custom_properties` output SHALL be an empty list
