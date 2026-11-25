# custom-property-assignments Specification

## Purpose

Define the requirements for assigning custom property values to repositories via YAML configuration: group
inheritance with repository overrides, value normalization, ordering after the definitions, account type
gating and validation of references, values and required properties.

## Requirements

### Requirement: Assign custom property values per repository

The system SHALL support a `custom_property_values:` map in both group and repository YAML configurations. Each key in
the map is a property name and each value is the property value to assign.

#### Scenario: Group-level property values

- **WHEN** a group defines `custom_property_values: { environment: production }`
- **AND** a repository belongs to that group
- **THEN** the system SHALL create a `github_repository_custom_property` resource assigning `environment = production`
  to that repository

#### Scenario: Repository-level override

- **WHEN** a group defines `custom_property_values: { compliance_level: none }`
- **AND** a repository in that group defines `custom_property_values: { compliance_level: soc2 }`
- **THEN** the system SHALL assign `compliance_level = soc2` to that repository (repo value overrides group)

#### Scenario: Multi-group merge

- **WHEN** a repository belongs to groups `["base", "oss"]`
- **AND** `base` defines `custom_property_values: { environment: development }`
- **AND** `oss` defines `custom_property_values: { environment: production, compliance_level: none }`
- **THEN** the system SHALL assign `environment = production` (last group wins) and `compliance_level = none`

#### Scenario: Absent or null block

- **WHEN** a group or repository has no `custom_property_values:` key, or defines it with no value
- **THEN** the system SHALL treat it as an empty map and assign nothing from it

### Requirement: Handle multi_select property values

The system SHALL accept list values for `multi_select` properties and scalar values (string, number or boolean) for all
other types (`string`, `single_select`, `true_false`). The Terraform layer SHALL normalize all values to the set of
strings expected by the `github_repository_custom_property` resource.

#### Scenario: Scalar value for single_select

- **WHEN** a repository has `custom_property_values: { environment: production }` and `environment` is `single_select`
- **THEN** the system SHALL pass `property_value = ["production"]` to the resource

#### Scenario: List value for multi_select

- **WHEN** a repository has `custom_property_values: { tags: [frontend, critical] }` and `tags` is `multi_select`
- **THEN** the system SHALL pass `property_value = ["frontend", "critical"]` to the resource

#### Scenario: Boolean value for true_false

- **WHEN** a repository has `custom_property_values: { is_deprecated: true }` and `is_deprecated` is `true_false`
- **THEN** the system SHALL pass `property_value = ["true"]` to the resource

### Requirement: Account type gating for property assignments

The system SHALL only create `github_repository_custom_property` resources when `is_organization` is `true`, whatever
the subscription tier. For a personal account, all property value assignments SHALL be skipped.

#### Scenario: Personal account skips property assignments

- **WHEN** `is_organization` is `false` and repositories have `custom_property_values:` defined
- **THEN** no `github_repository_custom_property` resources SHALL be created for any repository

#### Scenario: Free tier creates property assignments

- **WHEN** `subscription` is `free`, `is_organization` is `true`, and repositories have `custom_property_values:`
- **THEN** `github_repository_custom_property` resources SHALL be created for each property-value pair on each repository

### Requirement: Property definitions must exist before assignments

The system SHALL ensure that `github_organization_custom_properties` resources are created before any
`github_repository_custom_property` resources that reference them. This SHALL be enforced via Terraform's `depends_on`
mechanism on the repository module.

#### Scenario: Fresh deployment ordering

- **WHEN** both property definitions and property assignments are being created for the first time
- **THEN** Terraform SHALL create all property definition resources before creating any property assignment resources

### Requirement: Validate property references

The validation script SHALL verify that every property name used in `custom_property_values:` (in groups or
repositories) is defined in `config/custom-property/`, and `terraform plan` SHALL fail on the assignment resource for an
undefined name. Undefined references SHALL be reported as errors.

#### Scenario: Undefined property reference

- **WHEN** a group or repository references `custom_property_values: { nonexistent: value }`
- **AND** `nonexistent` is not defined in `config/custom-property/`
- **THEN** the validation script SHALL report an error identifying the undefined property name and the group/repo that
  references it
- **AND** `terraform plan` SHALL fail on the assignment resource for that repository

#### Scenario: All references valid

- **WHEN** all `custom_property_values:` keys match defined property names in `config/custom-property/`
- **THEN** the validation script SHALL report no property reference errors

### Requirement: Validate assigned values

The validation script SHALL verify that assigned values match the property's `value_type`, and `terraform plan` SHALL
fail on the assignment resource for the same violations. Violations SHALL be reported as errors:

- `string`, `single_select` and `true_false` take exactly one value; only `multi_select` takes a list
- `single_select` and `multi_select` values SHALL be in the property's `allowed_values`
- `true_false` values SHALL be `true` or `false`

#### Scenario: Invalid single_select value

- **WHEN** property `environment` has `allowed_values: [development, staging, production]`
- **AND** a repository assigns `custom_property_values: { environment: testing }`
- **THEN** the validation script SHALL report an error that `testing` is not in the allowed values for `environment`
- **AND** `terraform plan` SHALL fail on the assignment resource for that repository

#### Scenario: Valid multi_select values

- **WHEN** property `tags` has `allowed_values: [frontend, backend, critical]`
- **AND** a repository assigns `custom_property_values: { tags: [frontend, critical] }`
- **THEN** the validation script SHALL report no error for this assignment

#### Scenario: List for a single-value type

- **WHEN** property `environment` is `single_select`
- **AND** a repository assigns `custom_property_values: { environment: [development, staging] }`
- **THEN** the validation script SHALL report an error that `environment` takes exactly one value

### Requirement: Validate required properties have values

The validation script SHALL verify that every property marked `required: true` has a value for every managed
repository: either assigned (via group or repo-level `custom_property_values:`) or provided by the property's
`default_value`. A missing value SHALL be an error, and `terraform plan` SHALL fail on the property definition resource.
The check applies only to organizations.

#### Scenario: Required property missing on a repo

- **WHEN** property `environment` is `required: true` with no `default_value`
- **AND** repository `orphan-repo` has no `environment` in its effective `custom_property_values:`
- **THEN** the validation script SHALL report an error that `orphan-repo` is missing required property `environment`
- **AND** `terraform plan` SHALL fail on the definition resource for `environment`

#### Scenario: Required property satisfied via group

- **WHEN** property `environment` is `required: true`
- **AND** the repository's group assigns `custom_property_values: { environment: production }`
- **THEN** the validation script SHALL report no error for this repository

#### Scenario: Required property satisfied by default

- **WHEN** property `environment` is `required: true` with `default_value: development`
- **AND** a repository has no `environment` value
- **THEN** the validation script SHALL report no error for this repository
