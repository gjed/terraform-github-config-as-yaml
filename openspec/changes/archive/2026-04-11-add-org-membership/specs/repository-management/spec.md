# repository-management Specification (Delta)

## MODIFIED Requirements

### Requirement: YAML-Based Repository Configuration

The system SHALL read repository configurations from YAML files under the directory specified by
`var.config_path` using Terraform's native `yamldecode()` function. The default consumer layout
expected under `config_path` is: `config.yml` at the root, and sub-directories `group/`,
`repository/`, `ruleset/`, `webhook/`, and `membership/` containing `*.yml` files.

Split configuration applies to: `repository`, `group`, `ruleset`, and `membership` types. These
MUST be defined in directories using singular naming convention: `<config_path>/repository/`,
`<config_path>/group/`, `<config_path>/ruleset/`, `<config_path>/membership/`.

Organization-level settings (`<config_path>/config.yml`) remain a single file and do not support
splitting.

#### Scenario: Load common configuration

- **WHEN** Terraform is initialized and planned
- **THEN** the system reads `<config_path>/config.yml` as a single file
- **AND** parses organization name and subscription tier

#### Scenario: Load repository configuration from directory

- **GIVEN** a `<config_path>/repository/` directory exists with files `frontend.yml` and `backend.yml`
- **WHEN** Terraform is initialized and planned
- **THEN** the system reads all `.yml` files from the directory
- **AND** merges them alphabetically into a single configuration map

#### Scenario: Invalid YAML syntax

- **WHEN** a configuration file contains invalid YAML syntax
- **THEN** Terraform fails with a parsing error message indicating the file and location

#### Scenario: Load group configuration from directory

- **GIVEN** a `<config_path>/group/` directory exists with files `oss.yml` and `internal.yml`
- **WHEN** Terraform is initialized and planned
- **THEN** the system reads all `.yml` files from the directory
- **AND** merges them alphabetically into a single groups configuration map

#### Scenario: Load ruleset configuration from directory

- **GIVEN** a `<config_path>/ruleset/` directory exists
- **WHEN** Terraform is initialized and planned
- **THEN** the system reads all `.yml` files from the directory
- **AND** merges them alphabetically into a single rulesets configuration map

#### Scenario: Load membership configuration from directory

- **GIVEN** a `<config_path>/membership/` directory exists with files `engineering.yml` and
  `leadership.yml`
- **WHEN** Terraform is initialized and planned
- **THEN** the system reads all `.yml` files from the `membership/` directory
- **AND** merges them alphabetically into a single membership configuration map

#### Scenario: Empty directory fallback

- **GIVEN** a `<config_path>/repository/` directory exists but contains no `.yml` files
- **WHEN** Terraform is initialized and planned
- **THEN** the system uses an empty configuration map for repositories

#### Scenario: Duplicate keys across files in directory

- **GIVEN** a `<config_path>/repository/` directory contains two files both defining `my-repo`
- **WHEN** Terraform is initialized and planned
- **THEN** the later file (alphabetically) overrides the earlier one

#### Scenario: Missing directory

- **GIVEN** a `<config_path>/repository/` directory does not exist
- **WHEN** Terraform is initialized and planned
- **THEN** Terraform fails with an error indicating the required directory is missing

#### Scenario: Missing membership directory is not an error

- **GIVEN** a `<config_path>/membership/` directory does not exist
- **WHEN** Terraform is initialized and planned
- **THEN** the system uses an empty membership map
- **AND** no error is raised (membership directory is optional)

#### Scenario: Single file not supported for splittable types

- **GIVEN** only `<config_path>/repositories.yml` exists (no `<config_path>/repository/` directory)
- **WHEN** Terraform is initialized and planned
- **THEN** Terraform fails with an error indicating directory structure is required

#### Scenario: Consumer specifies custom config directory

- **WHEN** a consumer sets `config_path = "${path.root}/my-configs"`
- **THEN** the module reads YAML from `my-configs/` instead of any hardcoded path
