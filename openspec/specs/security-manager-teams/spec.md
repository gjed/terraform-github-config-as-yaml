# security-manager-teams Specification

## Purpose

Define the requirements for designating GitHub teams as security managers with organization-wide
security alert access.

## Requirements

### Requirement: Security Manager Team Designation

The system SHALL allow users to designate GitHub teams as security managers by listing team slugs
under `security.security_manager_teams` in `config/config.yml`. Each listed team slug SHALL result
in a `github_organization_role_team` resource that assigns the `security_manager` organization role
to that team.

#### Scenario: Single security manager team configured

- **WHEN** `config/config.yml` contains `security.security_manager_teams: ["security-team"]`
- **THEN** the system creates one `github_organization_role_team` resource
- **AND** the resource assigns the `security_manager` role to the team with slug `security-team`

#### Scenario: Multiple security manager teams configured

- **WHEN** `config/config.yml` contains `security.security_manager_teams: ["security-team", "platform-team"]`
- **THEN** the system creates two `github_organization_role_team` resources
- **AND** each resource assigns the `security_manager` role to its respective team slug

#### Scenario: Empty security manager teams list

- **WHEN** `config/config.yml` contains `security.security_manager_teams: []`
- **THEN** the system creates no `github_organization_role_team` resources

#### Scenario: No security section in config

- **WHEN** `config/config.yml` does not contain a `security` key
- **THEN** the system creates no security manager resources
- **AND** no errors are raised

### Requirement: Dynamic Role ID Lookup

The system SHALL look up the `security_manager` role ID dynamically using the
`github_organization_roles` data source rather than hardcoding the role ID. This ensures
compatibility across different GitHub organizations where role IDs may differ.

#### Scenario: Role ID resolved at plan time

- **WHEN** security manager teams are configured
- **THEN** the system uses `data.github_organization_roles` to look up available organization roles
- **AND** filters for the role with name `security_manager`
- **AND** uses the resolved `role_id` in each `github_organization_role_team` resource

### Requirement: Organization-Only Feature Gate

The system SHALL only create security manager resources when `is_organization` is `true` in the
common configuration. Security manager roles are an organization-level feature and do not apply
to personal GitHub accounts.

#### Scenario: Organization account with security managers

- **WHEN** `is_organization` is `true` (default)
- **AND** security manager teams are configured
- **THEN** the system creates the security manager resources

#### Scenario: Personal account with security managers configured

- **WHEN** `is_organization` is `false`
- **AND** security manager teams are configured
- **THEN** the system creates no security manager resources
- **AND** no errors are raised

### Requirement: Subscription Tier Gate

The system SHALL only create security manager resources when the subscription tier is `team` or
`enterprise`. The security manager role is not available on `free` or `pro` plans. When the
subscription tier does not support security managers, the resources SHALL be skipped silently.

#### Scenario: Team subscription with security managers

- **WHEN** `subscription` is `team`
- **AND** security manager teams are configured
- **THEN** the system creates the security manager resources

#### Scenario: Free subscription with security managers configured

- **WHEN** `subscription` is `free`
- **AND** security manager teams are configured
- **THEN** the system creates no security manager resources

#### Scenario: Enterprise subscription with security managers

- **WHEN** `subscription` is `enterprise`
- **AND** security manager teams are configured
- **THEN** the system creates the security manager resources

### Requirement: Validation of Security Configuration

The validation script (`scripts/validate-config.py`) SHALL validate the `security` section in
`config/config.yml`. It SHALL verify that `security_manager_teams` is a list of strings when
present, and SHALL warn when security manager teams are configured on an unsupported subscription
tier.

#### Scenario: Valid security configuration

- **WHEN** the validation script processes `config/config.yml`
- **AND** `security.security_manager_teams` is a list of strings
- **THEN** validation passes with no errors

#### Scenario: Invalid security_manager_teams type

- **WHEN** the validation script processes `config/config.yml`
- **AND** `security.security_manager_teams` is not a list (e.g., a string or number)
- **THEN** the validation script reports an error

#### Scenario: Subscription tier warning

- **WHEN** the validation script processes `config/config.yml`
- **AND** `security.security_manager_teams` is non-empty
- **AND** `subscription` is `free` or `pro`
- **THEN** the validation script reports a warning that security managers are not supported on the
  current subscription tier
