## ADDED Requirements

### Requirement: Archive-on-Destroy Safety Net

The repository submodule SHALL support an `archive_on_destroy` argument on the `github_repository`
resource. When set to `true`, the GitHub provider archives the repository instead of deleting it if
a destroy operation somehow proceeds (e.g., after `terraform state rm` and re-import).

#### Scenario: Default archive_on_destroy value

- **WHEN** `archive_on_destroy` is not specified in `config/config.yml` defaults
- **THEN** the system uses `false` as the default value
- **AND** all repositories have `archive_on_destroy = false` applied (current behavior preserved)

#### Scenario: Explicit archive_on_destroy in config defaults

- **GIVEN** `config/config.yml` contains:

  ```yaml
  defaults:
    archive_on_destroy: false
  ```

- **WHEN** Terraform is initialized and planned

- **THEN** all repositories have `archive_on_destroy = false` applied

#### Scenario: archive_on_destroy passed through to resource

- **GIVEN** `archive_on_destroy` is set to `true` in config defaults
- **WHEN** a repository resource is created
- **THEN** the `github_repository` resource includes `archive_on_destroy = true`

______________________________________________________________________

### Requirement: Validation Warning for Disabled Safety Net

The validation script SHALL warn when `archive_on_destroy` is explicitly set to `false` in
configuration, since this removes the secondary safety net.

#### Scenario: archive_on_destroy set to false

- **GIVEN** `config/config.yml` contains `defaults.archive_on_destroy: false`
- **WHEN** the validation script is executed
- **THEN** the script outputs a warning that the archive-on-destroy safety net is disabled

#### Scenario: archive_on_destroy set to true or absent

- **GIVEN** `config/config.yml` does not set `defaults.archive_on_destroy` or sets it to `true`
- **WHEN** the validation script is executed
- **THEN** no warning about archive-on-destroy is produced

______________________________________________________________________

### Requirement: Decommissioning Documentation

The module documentation SHALL describe the safe process for removing a repository from Terraform
management, including the behavior of `archive_on_destroy` as a secondary safety net.

#### Scenario: Documentation covers decommissioning

- **WHEN** a user reads the module documentation (AGENTS.md)
- **THEN** they find a section explaining:
  - The normal YAML-entry removal process for repositories
  - The role of `archive_on_destroy` as a secondary safety net (default: `false` in this release)
  - How to configure `archive_on_destroy` in `config/config.yml` defaults
