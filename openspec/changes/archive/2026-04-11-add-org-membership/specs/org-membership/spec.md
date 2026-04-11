# org-membership Specification

## Purpose

Define the requirements for managing GitHub organization membership via YAML configuration. This
covers loading membership definitions, creating `github_membership` resources, safety mechanisms,
and personal account handling.

## ADDED Requirements

### Requirement: Membership YAML Configuration

The system SHALL read membership configurations from YAML files under
`<config_path>/membership/` using the same split-file pattern as repositories, groups, and
rulesets. Each file contains a map of GitHub usernames to role strings.

#### Scenario: Load membership from single file

- **GIVEN** a `<config_path>/membership/` directory exists with file `members.yml` containing:
  ```yaml
  developer1: member
  org-admin: admin
  ```
- **WHEN** Terraform is initialized and planned
- **THEN** the system reads the file and parses two membership entries

#### Scenario: Load membership from multiple files

- **GIVEN** a `<config_path>/membership/` directory contains `engineering.yml` and `leadership.yml`
- **WHEN** Terraform is initialized and planned
- **THEN** the system reads all `.yml` files from the directory
- **AND** merges them alphabetically into a single membership map

#### Scenario: Duplicate username across files

- **GIVEN** `engineering.yml` defines `alice: member` and `leadership.yml` defines `alice: admin`
- **WHEN** Terraform is initialized and planned
- **THEN** the later file alphabetically (`leadership.yml`) overrides the earlier one
- **AND** `alice` is assigned role `admin`

#### Scenario: Empty membership directory

- **GIVEN** a `<config_path>/membership/` directory exists but contains no `.yml` files
- **WHEN** Terraform is initialized and planned
- **THEN** the system uses an empty membership map
- **AND** no `github_membership` resources are created

#### Scenario: Missing membership directory

- **GIVEN** a `<config_path>/membership/` directory does not exist
- **WHEN** Terraform is initialized and planned
- **THEN** the system uses an empty membership map
- **AND** no error is raised (membership is optional)

______________________________________________________________________

### Requirement: Membership Resource Creation

The system SHALL create `github_membership` resources for each entry in the membership
configuration when membership management is enabled.

#### Scenario: Create membership for member role

- **GIVEN** membership config contains `developer1: member`
- **AND** `membership_management_enabled` is `true`
- **WHEN** `terraform apply` is executed
- **THEN** a `github_membership` resource is created for `developer1` with role `member`

#### Scenario: Create membership for admin role

- **GIVEN** membership config contains `org-admin: admin`
- **AND** `membership_management_enabled` is `true`
- **WHEN** `terraform apply` is executed
- **THEN** a `github_membership` resource is created for `org-admin` with role `admin`

#### Scenario: Update membership role

- **GIVEN** `developer1` is currently `member` in the membership config
- **AND** the config is changed to `developer1: admin`
- **WHEN** `terraform apply` is executed
- **THEN** the `github_membership` resource is updated to role `admin`

#### Scenario: Remove membership

- **GIVEN** `developer1` exists in the membership config
- **AND** `developer1` is removed from all membership YAML files
- **WHEN** `terraform apply` is executed
- **THEN** the `github_membership` resource is destroyed
- **AND** the user is removed from the organization

______________________________________________________________________

### Requirement: Membership Opt-In Safety

The system SHALL require explicit opt-in before managing organization membership. This prevents
accidental member removal when the feature is first configured.

#### Scenario: Membership disabled by default

- **GIVEN** `membership_management_enabled` is not set (defaults to `false`)
- **AND** membership configuration exists in `<config_path>/membership/`
- **WHEN** `terraform plan` is executed
- **THEN** no `github_membership` resources appear in the plan

#### Scenario: Membership explicitly enabled

- **GIVEN** `membership_management_enabled` is set to `true`
- **AND** membership configuration exists in `<config_path>/membership/`
- **WHEN** `terraform plan` is executed
- **THEN** `github_membership` resources appear in the plan for each configured member

#### Scenario: Enable membership with empty directory

- **GIVEN** `membership_management_enabled` is set to `true`
- **AND** the `<config_path>/membership/` directory is empty or missing
- **WHEN** `terraform plan` is executed
- **THEN** no `github_membership` resources appear in the plan
- **AND** no error is raised

______________________________________________________________________

### Requirement: Personal Account Exclusion

The system SHALL NOT create membership resources for personal accounts, since
`github_membership` requires an organization.

#### Scenario: Personal account skips membership

- **GIVEN** `is_organization: false` is set in `config/config.yml`
- **AND** `membership_management_enabled` is `true`
- **AND** membership configuration exists
- **WHEN** `terraform plan` is executed
- **THEN** no `github_membership` resources appear in the plan

#### Scenario: Organization account manages membership

- **GIVEN** `is_organization: true` (or not set, since `true` is the default)
- **AND** `membership_management_enabled` is `true`
- **AND** membership configuration exists
- **WHEN** `terraform plan` is executed
- **THEN** `github_membership` resources appear in the plan

______________________________________________________________________

### Requirement: Valid Role Values

The system SHALL only accept `member` or `admin` as valid role values in membership
configuration.

#### Scenario: Valid member role

- **GIVEN** membership config contains `developer1: member`
- **WHEN** `terraform plan` is executed
- **THEN** the plan succeeds

#### Scenario: Valid admin role

- **GIVEN** membership config contains `org-admin: admin`
- **WHEN** `terraform plan` is executed
- **THEN** the plan succeeds

#### Scenario: Invalid role in validation script

- **GIVEN** membership config contains `developer1: maintainer`
- **WHEN** `scripts/validate-config.py` is executed
- **THEN** the script reports an error indicating `maintainer` is not a valid role
- **AND** valid roles are `member` and `admin`

______________________________________________________________________

### Requirement: Duplicate Membership Detection

The system SHALL detect duplicate usernames across membership configuration files and report
them, following the same pattern as duplicate repository/group/ruleset key detection.

#### Scenario: Duplicate username warning

- **GIVEN** `engineering.yml` defines `alice: member`
- **AND** `leadership.yml` defines `alice: admin`
- **WHEN** `terraform plan` is executed
- **THEN** the system detects the duplicate
- **AND** includes it in the `duplicate_key_warnings` output
