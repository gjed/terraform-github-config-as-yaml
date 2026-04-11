# Spec Delta: Repository Management

## ADDED Requirements

### Requirement: Branch Protection Definitions

The system SHALL support branch protection definitions in the `config/branch-protection/`
directory. Each definition is a named branch protection rule that can be referenced from groups
or repositories.

#### Scenario: Load branch protection definitions from directory

- **GIVEN** a `config/branch-protection/` directory exists with files `main.yml` and `release.yml`
- **WHEN** Terraform is initialized and planned
- **THEN** the system reads all `.yml` files from the directory
- **AND** merges them alphabetically into a single branch protections definition map

#### Scenario: Branch protection definition structure

- **GIVEN** a branch protection is defined in `config/branch-protection/default-protections.yml`:
  ```yaml
  main-protection:
    pattern: "main"
    enforce_admins: true
    allows_deletions: false
    allows_force_pushes: false
    lock_branch: false
    require_conversation_resolution: true
    require_signed_commits: false
    required_linear_history: false
    required_pull_request_reviews:
      required_approving_review_count: 1
      dismiss_stale_reviews: true
    required_status_checks:
      strict: true
      contexts:
        - "ci/build"
  ```
- **WHEN** Terraform parses the configuration
- **THEN** the branch protection is available to reference by name `main-protection`

#### Scenario: Missing branch protection directory

- **GIVEN** a `config/branch-protection/` directory does not exist
- **WHEN** Terraform is initialized and planned
- **THEN** the system uses an empty branch protections map
- **AND** no error is raised (branch protections are optional)

#### Scenario: Empty branch protection directory

- **GIVEN** a `config/branch-protection/` directory exists but contains no `.yml` files
- **WHEN** Terraform is initialized and planned
- **THEN** the system uses an empty branch protections map

#### Scenario: Duplicate keys across files in directory

- **GIVEN** two files in `config/branch-protection/` both define `main-protection`
- **WHEN** Terraform is initialized and planned
- **THEN** the later file (alphabetically) overrides the earlier one
- **AND** a duplicate key warning is included in the `duplicate_config_keys` output

______________________________________________________________________

### Requirement: Branch Protection Configuration

The system SHALL support repository branch protection configuration by referencing named
definitions from `config/branch-protection/`. Branch protections can be assigned at the group
or repository level.

#### Scenario: Reference branch protection by name in repository

- **GIVEN** a branch protection `main-protection` is defined in `config/branch-protection/`
- **AND** a repository references it in `config/repository/my-repo.yml`:
  ```yaml
  my-repo:
    description: "My repo"
    groups: ["oss"]
    branch_protections:
      - main-protection
  ```
- **WHEN** `terraform apply` is executed
- **THEN** a `github_branch_protection` resource is created on the repository
- **AND** the protection targets the branch pattern defined in `main-protection`

#### Scenario: Reference branch protection by name in group

- **GIVEN** a branch protection `main-protection` is defined in `config/branch-protection/`
- **AND** group `oss` references it:
  ```yaml
  oss:
    branch_protections:
      - main-protection
  ```
- **AND** a repository uses group `oss`
- **WHEN** `terraform apply` is executed
- **THEN** the `main-protection` branch protection is created on the repository

#### Scenario: Multiple branch protections on one repository

- **GIVEN** a repository references `branch_protections: ["main-protection", "release-protection"]`
- **AND** `main-protection` targets pattern `main`
- **AND** `release-protection` targets pattern `release/*`
- **WHEN** `terraform apply` is executed
- **THEN** two `github_branch_protection` resources are created on the repository

#### Scenario: Reference undefined branch protection

- **GIVEN** a repository references `branch_protections: ["nonexistent"]`
- **AND** no definition named `nonexistent` exists in `config/branch-protection/`
- **WHEN** `terraform plan` is executed
- **THEN** Terraform fails with an error indicating the branch protection is not defined

#### Scenario: Branch protection with all options

- **GIVEN** a branch protection is defined with all configuration options:
  ```yaml
  full-protection:
    pattern: "main"
    enforce_admins: true
    allows_deletions: false
    allows_force_pushes: false
    lock_branch: true
    require_conversation_resolution: true
    require_signed_commits: true
    required_linear_history: true
    required_pull_request_reviews:
      required_approving_review_count: 2
      dismiss_stale_reviews: true
      require_code_owner_reviews: true
      require_last_push_approval: true
      restrict_dismissals: true
      dismissal_restrictions:
        users: ["lead-dev"]
        teams: ["senior-devs"]
        apps: []
      pull_request_bypassers:
        users: ["release-bot"]
        teams: ["admins"]
        apps: []
    required_status_checks:
      strict: true
      contexts:
        - "ci/build"
        - "ci/test"
        - "security/scan"
    restrict_pushes:
      blocks_creations: true
      push_allowances:
        users: ["release-bot"]
        teams: ["devops"]
        apps: []
  ```
- **WHEN** `terraform apply` is executed
- **THEN** the branch protection is created with all specified settings

#### Scenario: Branch protection with minimal options

- **GIVEN** a branch protection is defined with only the required field:
  ```yaml
  minimal-protection:
    pattern: "main"
  ```
- **WHEN** `terraform apply` is executed
- **THEN** the branch protection is created with default values for all optional fields
- **AND** `enforce_admins` defaults to `false`
- **AND** `allows_deletions` defaults to `false`
- **AND** `allows_force_pushes` defaults to `false`
- **AND** `lock_branch` defaults to `false`
- **AND** no `required_pull_request_reviews` block is created
- **AND** no `required_status_checks` block is created
- **AND** no `restrict_pushes` block is created

______________________________________________________________________

### Requirement: Branch Protection Inheritance from Groups

The system SHALL support branch protection inheritance from configuration groups using the same
merging strategy as rulesets: collected from groups in order, repo-specific appended, deduplicated
by name with later values overriding earlier ones.

#### Scenario: Inherit branch protections from group

- **GIVEN** group `oss` defines `branch_protections: ["main-protection"]`
- **AND** a repository uses `groups: ["oss"]`
- **AND** the repository does not define its own `branch_protections`
- **WHEN** the configuration is merged
- **THEN** the repository has branch protection `main-protection` applied

#### Scenario: Combine group and repository branch protections

- **GIVEN** group `oss` defines `branch_protections: ["main-protection"]`
- **AND** a repository defines `branch_protections: ["release-protection"]`
- **WHEN** the configuration is merged
- **THEN** both `main-protection` and `release-protection` are applied to the repository

#### Scenario: Multiple groups with branch protections

- **GIVEN** group `base` defines `branch_protections: ["main-protection"]`
- **AND** group `strict` defines `branch_protections: ["strict-main"]`
- **AND** a repository uses `groups: ["base", "strict"]`
- **WHEN** the configuration is merged
- **THEN** both `main-protection` and `strict-main` are applied to the repository

#### Scenario: Later group overrides earlier group by name

- **GIVEN** group `base` references `main-protection` defined with `enforce_admins: false`
- **AND** group `strict` also references `main-protection` (same name, same definition resolved)
- **AND** a repository uses `groups: ["base", "strict"]`
- **WHEN** the configuration is merged
- **THEN** `main-protection` appears only once (deduplicated by name)

#### Scenario: Repository branch protection overrides group

- **GIVEN** group `oss` references `main-protection`
- **AND** the repository also references `main-protection`
- **WHEN** the configuration is merged
- **THEN** `main-protection` appears only once (deduplicated by name)

______________________________________________________________________

### Requirement: Branch Protection Coexistence with Rulesets

The system SHALL allow both rulesets and branch protections to be configured on the same
repository simultaneously. The two mechanisms are independent and do not interact with each other
at the Terraform configuration level.

#### Scenario: Repository with both rulesets and branch protections

- **GIVEN** a repository defines:
  ```yaml
  my-repo:
    description: "My repo"
    groups: ["oss"]
    rulesets:
      - oss-main-protection
    branch_protections:
      - main-protection
  ```
- **WHEN** `terraform apply` is executed
- **THEN** both `github_repository_ruleset` and `github_branch_protection` resources are created
- **AND** they target the repository independently

#### Scenario: Group with both rulesets and branch protections

- **GIVEN** a group defines both `rulesets` and `branch_protections`:
  ```yaml
  secure:
    rulesets:
      - oss-main-protection
    branch_protections:
      - main-protection
  ```
- **AND** a repository uses group `secure`
- **WHEN** `terraform apply` is executed
- **THEN** both the ruleset and the branch protection are applied to the repository

______________________________________________________________________

## MODIFIED Requirements

### Requirement: YAML-Based Repository Configuration (MODIFIED)

**Addition:** The system SHALL optionally read branch protection definitions from
`config/branch-protection/` if the directory exists. This directory follows the same conventions
as other split-config directories (`.yml` files, alphabetical merge, duplicate detection) but is
optional rather than required.

#### Scenario: Load branch protection configuration from directory

- **GIVEN** a `config/branch-protection/` directory exists with `.yml` files
- **WHEN** Terraform is initialized and planned
- **THEN** the system reads all `.yml` files from the directory
- **AND** merges them alphabetically into a single branch protections definition map

______________________________________________________________________

### Requirement: Configuration Merging Strategy (MODIFIED)

**Addition:** The system SHALL merge branch protections using the same list-based strategy as
rulesets: collected from groups in order, repo-specific appended, deduplicated by name.

#### Scenario: Branch protection merging

- **GIVEN** group `base` defines `branch_protections: ["main-protection"]`
- **AND** repository defines `branch_protections: ["release-protection"]`
- **WHEN** the configuration is merged
- **THEN** the repository has branch protections `["main-protection", "release-protection"]`

______________________________________________________________________

### Requirement: Output Values (MODIFIED)

**Addition:** The system SHALL include duplicate branch protection key warnings in the
`duplicate_config_keys` output alongside existing repository, group, and ruleset duplicate warnings.

#### Scenario: Duplicate branch protection key warning

- **WHEN** two files in `config/branch-protection/` both define `main-protection`
- **AND** `terraform apply` completes
- **THEN** the `duplicate_config_keys` output includes the branch protection duplicate with
  the affected file names
