## ADDED Requirements

### Requirement: YAML-Based Team Configuration

The system SHALL read team configurations from YAML files under `<config_path>/team/` using the
same split-directory pattern as repositories, groups, and rulesets.

#### Scenario: Load team configuration from directory

- **GIVEN** a `<config_path>/team/` directory exists with files `engineering.yml` and `security.yml`
- **WHEN** Terraform is initialized and planned
- **THEN** the system reads all `.yml` files from the directory
- **AND** merges them alphabetically into a single teams configuration map

#### Scenario: Empty team directory

- **GIVEN** a `<config_path>/team/` directory exists but contains no `.yml` files
- **WHEN** Terraform is initialized and planned
- **THEN** the system uses an empty teams configuration map
- **AND** no team resources are created

#### Scenario: Missing team directory

- **GIVEN** a `<config_path>/team/` directory does not exist
- **WHEN** Terraform is initialized and planned
- **THEN** the system uses an empty teams configuration map
- **AND** no team resources are created
- **AND** no error is raised (teams are optional)

#### Scenario: Duplicate team slugs across files

- **GIVEN** `engineering.yml` defines a top-level team `platform`
- **AND** `platform.yml` also defines a top-level team `platform`
- **WHEN** Terraform is initialized and planned
- **THEN** the later file (alphabetically) overrides the earlier one

______________________________________________________________________

### Requirement: Team Creation and Configuration

The system SHALL create and manage GitHub teams using the `github_team` resource.

#### Scenario: Create a root team

- **GIVEN** a team is defined in `config/team/engineering.yml`:
  ```yaml
  engineering:
    description: "Engineering org"
    privacy: closed
  ```
- **WHEN** `terraform apply` is executed
- **THEN** a `github_team` resource is created with name `engineering`
- **AND** description is set to `"Engineering org"`
- **AND** privacy is set to `closed`

#### Scenario: Default privacy

- **GIVEN** a team is defined without a `privacy` field
- **WHEN** `terraform apply` is executed
- **THEN** the team is created with privacy `closed`

#### Scenario: Secret team

- **GIVEN** a team defines `privacy: secret`
- **WHEN** `terraform apply` is executed
- **THEN** the team is created with privacy `secret`
- **AND** the team is only visible to organization owners and team members

#### Scenario: Update team description

- **GIVEN** an existing managed team's description is changed in YAML
- **WHEN** `terraform apply` is executed
- **THEN** the team's description is updated in GitHub

#### Scenario: Organization-only guard

- **GIVEN** `is_organization: false` in `config.yml`
- **AND** teams are defined in `config/team/`
- **WHEN** Terraform is initialized and planned
- **THEN** no team resources are created
- **AND** no error is raised

______________________________________________________________________

### Requirement: Nested Team Hierarchy

The system SHALL support nested team definitions up to 3 levels deep (root, child, grandchild)
using a nested `teams` key within team definitions.

#### Scenario: One level of nesting

- **GIVEN** a team definition:
  ```yaml
  engineering:
    description: "Engineering org"
    teams:
      platform-team:
        description: "Platform engineering"
  ```
- **WHEN** `terraform apply` is executed
- **THEN** team `engineering` is created first (tier 0)
- **AND** team `platform-team` is created with `parent_team_id` referencing `engineering` (tier 1)

#### Scenario: Two levels of nesting

- **GIVEN** a team definition:
  ```yaml
  engineering:
    description: "Engineering org"
    teams:
      platform-team:
        description: "Platform engineering"
        teams:
          platform-sre:
            description: "SRE sub-team"
  ```
- **WHEN** `terraform apply` is executed
- **THEN** `engineering` is created first (tier 0)
- **AND** `platform-team` is created second with parent `engineering` (tier 1)
- **AND** `platform-sre` is created third with parent `platform-team` (tier 2)

#### Scenario: Maximum nesting depth exceeded

- **GIVEN** a team definition nests teams 4 levels deep
- **WHEN** Terraform is initialized and planned
- **THEN** a validation error is raised indicating the maximum nesting depth of 3 is exceeded

#### Scenario: Multiple children under one parent

- **GIVEN** a team definition:
  ```yaml
  engineering:
    description: "Engineering org"
    teams:
      platform-team:
        description: "Platform"
      frontend-team:
        description: "Frontend"
      backend-team:
        description: "Backend"
  ```
- **WHEN** `terraform apply` is executed
- **THEN** `engineering` is created first
- **AND** all three child teams are created with `parent_team_id` referencing `engineering`

#### Scenario: Unique slugs across hierarchy

- **GIVEN** a root team `platform` exists
- **AND** a child team also named `platform` is nested under another team
- **WHEN** Terraform is initialized and planned
- **THEN** a validation error is raised indicating duplicate team slug `platform`

______________________________________________________________________

### Requirement: Team Membership Management

The system SHALL manage team membership using the `github_team_membership` resource when
`members` or `maintainers` lists are defined.

#### Scenario: Add members to a team

- **GIVEN** a team defines:
  ```yaml
  platform-team:
    description: "Platform engineering"
    members:
      - user1
      - user2
  ```
- **WHEN** `terraform apply` is executed
- **THEN** `user1` and `user2` are added to `platform-team` with role `member`

#### Scenario: Add maintainers to a team

- **GIVEN** a team defines:
  ```yaml
  platform-team:
    description: "Platform engineering"
    maintainers:
      - lead1
  ```
- **WHEN** `terraform apply` is executed
- **THEN** `lead1` is added to `platform-team` with role `maintainer`

#### Scenario: Both members and maintainers

- **GIVEN** a team defines both `members` and `maintainers`
- **WHEN** `terraform apply` is executed
- **THEN** members are added with role `member`
- **AND** maintainers are added with role `maintainer`

#### Scenario: No membership defined

- **GIVEN** a team defines neither `members` nor `maintainers`
- **WHEN** `terraform apply` is executed
- **THEN** the team is created without any `github_team_membership` resources
- **AND** membership is not managed by Terraform

#### Scenario: Remove a member

- **GIVEN** a user is removed from a team's `members` list in YAML
- **WHEN** `terraform apply` is executed
- **THEN** the user's `github_team_membership` resource is destroyed
- **AND** the user is removed from the team

#### Scenario: User in both members and maintainers

- **GIVEN** `user1` appears in both `members` and `maintainers` for the same team
- **WHEN** Terraform is initialized and planned
- **THEN** a validation error is raised indicating the user cannot be in both lists

______________________________________________________________________

### Requirement: PR Review Request Delegation

The system SHALL manage PR review request delegation settings using the `github_team_settings`
resource when `review_request_delegation` is defined.

#### Scenario: Enable review request delegation

- **GIVEN** a team defines:
  ```yaml
  platform-team:
    description: "Platform engineering"
    review_request_delegation:
      enabled: true
      algorithm: round_robin
      member_count: 2
      notify: true
  ```
- **WHEN** `terraform apply` is executed
- **THEN** a `github_team_settings` resource is created for `platform-team`
- **AND** review request delegation is enabled with round robin algorithm
- **AND** 2 members are assigned per review request
- **AND** the whole team is notified

#### Scenario: Load balance algorithm

- **GIVEN** a team defines `review_request_delegation.algorithm: load_balance`
- **WHEN** `terraform apply` is executed
- **THEN** the delegation uses the load balance algorithm

#### Scenario: Default delegation values

- **GIVEN** a team defines `review_request_delegation: { enabled: true }`
- **WHEN** `terraform apply` is executed
- **THEN** the algorithm defaults to `round_robin`
- **AND** the member count defaults to `1`
- **AND** notify defaults to `true`

#### Scenario: No delegation configured

- **GIVEN** a team does not define `review_request_delegation`
- **WHEN** `terraform apply` is executed
- **THEN** no `github_team_settings` resource is created for the team
- **AND** the team uses GitHub's default review request behavior

#### Scenario: Disable delegation

- **GIVEN** a team defines `review_request_delegation: { enabled: false }`
- **WHEN** `terraform apply` is executed
- **THEN** a `github_team_settings` resource is created with delegation disabled

______________________________________________________________________

### Requirement: Team Configuration Validation

The system SHALL validate team configuration for correctness at plan time and via the validation
script.

#### Scenario: Required description field

- **GIVEN** a team is defined without a `description` field
- **WHEN** the validation script runs
- **THEN** an error is reported indicating `description` is required

#### Scenario: Invalid privacy value

- **GIVEN** a team defines `privacy: public`
- **WHEN** the validation script runs
- **THEN** an error is reported indicating valid values are `closed` or `secret`

#### Scenario: Nesting depth validation

- **GIVEN** teams are nested 4 levels deep
- **WHEN** the validation script runs
- **THEN** an error is reported indicating maximum depth of 3 levels exceeded

#### Scenario: Duplicate slug detection

- **GIVEN** two teams with the same slug exist at different nesting levels
- **WHEN** the validation script runs
- **THEN** an error is reported indicating duplicate team slug

#### Scenario: Cross-reference warning for repo team assignments

- **GIVEN** a repository references `teams: { platform-team: push }`
- **AND** no team named `platform-team` is defined in `config/team/`
- **WHEN** the validation script runs
- **THEN** a warning is issued indicating the team slug is not managed
- **AND** this is a warning, not an error (teams can be managed externally)

#### Scenario: Invalid review delegation algorithm

- **GIVEN** a team defines `review_request_delegation.algorithm: random`
- **WHEN** the validation script runs
- **THEN** an error is reported indicating valid values are `round_robin` or `load_balance`

______________________________________________________________________

### Requirement: Team Outputs

The system SHALL output information about managed teams.

#### Scenario: Managed teams output

- **WHEN** `terraform apply` completes with teams defined
- **THEN** the system outputs a map of team slug to team ID for all managed teams

#### Scenario: No teams defined

- **WHEN** `terraform apply` completes without any teams defined
- **THEN** the managed teams output is an empty map
