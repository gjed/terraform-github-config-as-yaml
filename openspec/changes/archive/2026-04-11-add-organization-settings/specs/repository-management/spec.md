## ADDED Requirements

### Requirement: Organization Settings Configuration

The system SHALL support an optional `settings:` block in `config/config.yml` that maps to the
`github_organization_settings` Terraform resource. This block SHALL only be applied when
`is_organization: true` (the default). When the block is absent, no organization settings resource
is created and existing organization settings are left unchanged.

#### Scenario: Settings block absent — no resource created

- **GIVEN** `config/config.yml` contains no `settings:` key
- **WHEN** Terraform is planned
- **THEN** no `github_organization_settings` resource appears in the plan
- **AND** existing organization settings are not touched

#### Scenario: Settings block present — resource created

- **GIVEN** `config/config.yml` contains a `settings:` block with at least one key
- **AND** `is_organization: true` (default)
- **WHEN** Terraform is planned
- **THEN** a `github_organization_settings` resource is included in the plan
- **AND** each configured key is reflected in the resource attributes

#### Scenario: Personal account — settings block ignored

- **GIVEN** `config/config.yml` sets `is_organization: false`
- **AND** a `settings:` block is present
- **WHEN** Terraform is planned
- **THEN** no `github_organization_settings` resource is created
- **AND** a warning or documentation note advises the user the block is ignored

______________________________________________________________________

### Requirement: Supported Organization Settings Keys

The `settings:` block SHALL support the following keys, all optional:

- `default_repository_permission` (string: `none` | `read` | `write` | `admin`)
- `members_can_create_repositories` (bool)
- `members_can_create_public_repositories` (bool)
- `members_can_create_private_repositories` (bool)
- `members_can_create_internal_repositories` (bool, Enterprise only)
- `members_can_fork_private_repositories` (bool)
- `web_commit_signoff_required` (bool)
- `two_factor_requirement` (bool)
- `dependabot_alerts_enabled_for_new_repositories` (bool)
- `dependabot_security_updates_enabled_for_new_repositories` (bool)
- `dependency_graph_enabled_for_new_repositories` (bool)
- `secret_scanning_enabled_for_new_repositories` (bool, Enterprise/GHAS only)
- `secret_scanning_push_protection_enabled_for_new_repositories` (bool, Enterprise/GHAS only)
- `advanced_security_enabled_for_new_repositories` (bool, Enterprise/GHAS only)
- `blog` (string)
- `company` (string)
- `description` (string)
- `email` (string)
- `location` (string)

#### Scenario: Member permission configured

- **GIVEN** `settings.default_repository_permission: read`
- **WHEN** Terraform is applied
- **THEN** the `github_organization_settings` resource attribute `default_repository_permission` equals `"read"`

#### Scenario: Profile fields configured

- **GIVEN** `settings.company: "ACME Corp"` and `settings.location: "Berlin"`
- **WHEN** Terraform is applied
- **THEN** the resource attributes `company` and `location` reflect the configured values

______________________________________________________________________

### Requirement: Enterprise-Only Settings Gating

Settings that require GitHub Advanced Security (GHAS) or Enterprise subscription SHALL be omitted
from the resource when the `subscription` tier is not `enterprise`. The system SHALL emit a warning
for each skipped setting.

GHAS/Enterprise-only settings:

- `secret_scanning_enabled_for_new_repositories`
- `secret_scanning_push_protection_enabled_for_new_repositories`
- `advanced_security_enabled_for_new_repositories`
- `members_can_create_internal_repositories`

#### Scenario: GHAS setting on non-enterprise tier

- **GIVEN** `subscription: team`
- **AND** `settings.secret_scanning_enabled_for_new_repositories: true`
- **WHEN** Terraform is planned
- **THEN** the `github_organization_settings` resource does NOT include `secret_scanning_enabled_for_new_repositories`
- **AND** `subscription_warnings` output contains an entry noting the setting was skipped

#### Scenario: GHAS setting on enterprise tier

- **GIVEN** `subscription: enterprise`
- **AND** `settings.secret_scanning_enabled_for_new_repositories: true`
- **WHEN** Terraform is planned
- **THEN** the `github_organization_settings` resource includes the attribute set to `true`

______________________________________________________________________

### Requirement: Two-Factor Enforcement Warning

The module documentation and validation script SHALL include a prominent warning when
`settings.two_factor_requirement: true` is configured, making clear that this setting immediately
removes any organization members who do not have two-factor authentication enabled on their GitHub
account.

#### Scenario: 2FA enforcement documented

- **WHEN** a user reads the documentation for the `settings.two_factor_requirement` key
- **THEN** they see a clearly visible warning explaining the immediate member-removal behavior

#### Scenario: Validation script warns on 2FA

- **GIVEN** `settings.two_factor_requirement: true` is set in `config/config.yml`
- **WHEN** the user runs `scripts/validate-config.py`
- **THEN** the script prints a visible warning about the immediate membership impact
