## MODIFIED Requirements

### Requirement: YAML-Based Repository Configuration

The system SHALL read repository configurations from YAML files under the directory specified by
`var.config_path` using Terraform's native `yamldecode()` function. The default consumer layout
expected under `config_path` is: `config.yml` at the root, and sub-directories `group/`,
`repository/`, `ruleset/`, and `webhook/` containing `*.yml` files.

Split configuration applies to: `repository`, `group`, and `ruleset` types only. These MUST be
defined in directories using singular naming convention: `<config_path>/repository/`,
`<config_path>/group/`, `<config_path>/ruleset/`.

Organization-level settings (`<config_path>/config.yml`) remain a single file and do not support
splitting. The common configuration file SHALL support an optional `security` section for
organization-level security settings.

#### Scenario: Load common configuration

- **WHEN** Terraform is initialized and planned
- **THEN** the system reads `<config_path>/config.yml` as a single file
- **AND** parses organization name, subscription tier, and optional security configuration

#### Scenario: Load common configuration with security section

- **WHEN** Terraform is initialized and planned
- **AND** `<config_path>/config.yml` contains a `security` section
- **THEN** the system parses the security configuration including `security_manager_teams`
- **AND** makes the security configuration available for org-level resource creation

#### Scenario: Load common configuration without security section

- **WHEN** Terraform is initialized and planned
- **AND** `<config_path>/config.yml` does not contain a `security` section
- **THEN** the system uses a null/empty default for security configuration
- **AND** no security-related resources are created
