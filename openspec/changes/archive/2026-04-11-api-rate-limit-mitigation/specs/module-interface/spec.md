## MODIFIED Requirements

### Requirement: Module input variables

The module SHALL accept a `repository_partitions` variable in addition to all existing variables. The variable SHALL be of type `list(string)` with a default of `[]` (empty list). It SHALL be documented with a description explaining its purpose.

#### Scenario: Default value preserves backward compatibility

- **WHEN** a consumer does not set `repository_partitions`
- **THEN** the module SHALL behave identically to the current implementation, loading all repository config files

#### Scenario: Consumer sets specific partitions

- **WHEN** a consumer sets `repository_partitions = ["infra", "platform"]`
- **THEN** the module SHALL load only top-level repository files plus files from the `infra` and `platform` subdirectories

#### Scenario: Variable is documented

- **WHEN** a consumer runs `terraform docs` or reads `variables.tf`
- **THEN** the `repository_partitions` variable SHALL have a description explaining that it controls which repository subdirectories are loaded and that an empty list means all
