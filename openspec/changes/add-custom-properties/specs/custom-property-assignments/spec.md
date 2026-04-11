## ADDED Requirements

### Requirement: Assign custom property values per repository

The system SHALL support a `custom_property_values:` map in both group and repository YAML configurations. Each key in the map is a property name and each value is the property value to assign.

#### Scenario: Group-level property values

- **WHEN** a group defines `custom_property_values: { environment: production }`
- **AND** a repository belongs to that group
- **THEN** the system SHALL create a `github_repository_custom_property` resource assigning `environment = production` to that repository

#### Scenario: Repository-level override

- **WHEN** a group defines `custom_property_values: { compliance_level: none }`
- **AND** a repository in that group defines `custom_property_values: { compliance_level: soc2 }`
- **THEN** the system SHALL assign `compliance_level = soc2` to that repository (repo value overrides group)

#### Scenario: Multi-group merge

- **WHEN** a repository belongs to groups `["base", "oss"]`
- **AND** `base` defines `custom_property_values: { environment: development }`
- **AND** `oss` defines `custom_property_values: { environment: production, compliance_level: none }`
- **THEN** the system SHALL assign `environment = production` (last group wins) and `compliance_level = none`

### Requirement: Handle multi_select property values

The system SHALL accept list values for `multi_select` properties and scalar string values for all other types (`string`, `single_select`, `true_false`). The Terraform layer SHALL normalize all values to the list format expected by the `github_repository_custom_property` resource.

#### Scenario: Scalar value for single_select

- **WHEN** a repository has `custom_property_values: { environment: production }` and `environment` is `single_select`
- **THEN** the system SHALL pass `property_value = ["production"]` to the resource

#### Scenario: List value for multi_select

- **WHEN** a repository has `custom_property_values: { tags: [frontend, critical] }` and `tags` is `multi_select`
- **THEN** the system SHALL pass `property_value = ["frontend", "critical"]` to the resource

### Requirement: Subscription tier gating for property assignments

The system SHALL only create `github_repository_custom_property` resources when the subscription tier supports custom properties (`team` or `enterprise`) AND `is_organization` is `true`. On unsupported configurations, all property value assignments SHALL be skipped.

#### Scenario: Free tier skips property assignments

- **WHEN** `subscription` is `free` and repositories have `custom_property_values:` defined
- **THEN** no `github_repository_custom_property` resources SHALL be created for any repository

#### Scenario: Team tier creates property assignments

- **WHEN** `subscription` is `team`, `is_organization` is `true`, and repositories have `custom_property_values:`
- **THEN** `github_repository_custom_property` resources SHALL be created for each property-value pair on each repository

### Requirement: Property definitions must exist before assignments

The system SHALL ensure that `github_organization_custom_properties` resources are created before any `github_repository_custom_property` resources that reference them. This SHALL be enforced via Terraform's `depends_on` mechanism on the repository module.

#### Scenario: Fresh deployment ordering

- **WHEN** both property definitions and property assignments are being created for the first time
- **THEN** Terraform SHALL create all property definition resources before creating any property assignment resources

### Requirement: Validate property references

The validation script SHALL verify that every property name used in `custom_property_values:` (in groups or repositories) is defined in `config/custom-property/`. Undefined references SHALL be reported as validation errors.

#### Scenario: Undefined property reference

- **WHEN** a group or repository references `custom_property_values: { nonexistent: value }`
- **AND** `nonexistent` is not defined in `config/custom-property/`
- **THEN** the validation script SHALL report an error identifying the undefined property name and the group/repo that references it

#### Scenario: All references valid

- **WHEN** all `custom_property_values:` keys match defined property names in `config/custom-property/`
- **THEN** the validation script SHALL report no property reference errors

### Requirement: Validate select-type values

The validation script SHALL verify that values assigned to `single_select` and `multi_select` properties are in the property's `allowed_values` list. Invalid values SHALL be reported as validation errors.

#### Scenario: Invalid single_select value

- **WHEN** property `environment` has `allowed_values: [development, staging, production]`
- **AND** a repository assigns `custom_property_values: { environment: testing }`
- **THEN** the validation script SHALL report an error that `testing` is not in the allowed values for `environment`

#### Scenario: Valid multi_select values

- **WHEN** property `tags` has `allowed_values: [frontend, backend, critical]`
- **AND** a repository assigns `custom_property_values: { tags: [frontend, critical] }`
- **THEN** the validation script SHALL report no error for this assignment

### Requirement: Validate required properties have assignments

The validation script SHALL verify that every property marked `required: true` has a value assigned (via group or repo-level `custom_property_values:`) for every managed repository when the subscription tier supports custom properties.

#### Scenario: Required property missing on a repo

- **WHEN** property `environment` is `required: true`
- **AND** repository `orphan-repo` has no `environment` in its effective `custom_property_values:`
- **THEN** the validation script SHALL report a warning that `orphan-repo` is missing required property `environment`

#### Scenario: Required property satisfied via group

- **WHEN** property `environment` is `required: true`
- **AND** the repository's group assigns `custom_property_values: { environment: production }`
- **THEN** the validation script SHALL report no warning for this repository
