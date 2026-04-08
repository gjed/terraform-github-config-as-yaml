# Repository Management Capability

## ADDED Requirements

### Requirement: YAML-Based Repository Configuration

The system SHALL read repository configurations from YAML files in the `config/` directory using
Terraform's native `yamldecode()` function.

#### Scenario: Load configuration files

- **WHEN** Terraform is initialized and planned
- **THEN** the system reads `config/config.yml`, `config/groups.yml`, `config/repositories.yml`, and
  `config/rulesets.yml`
- **AND** parses them into Terraform local values

#### Scenario: Invalid YAML syntax

- **WHEN** a configuration file contains invalid YAML syntax
- **THEN** Terraform fails with a parsing error message indicating the file and location

______________________________________________________________________

### Requirement: Configuration Groups

The system SHALL support named configuration groups that define shared repository settings.

#### Scenario: Single group inheritance

- **WHEN** a repository specifies `groups: ["oss"]`
- **THEN** all settings from the `oss` group are applied to the repository

#### Scenario: Multiple group inheritance

- **WHEN** a repository specifies `groups: ["base", "oss"]`
- **THEN** settings from `base` are applied first
- **AND** settings from `oss` override conflicting values from `base`

#### Scenario: Repository-level overrides

- **WHEN** a repository specifies both a group and an explicit setting (e.g., `has_wiki: true`)
- **THEN** the explicit setting overrides the group setting

______________________________________________________________________

### Requirement: Configuration Merging Strategy

The system SHALL merge configurations from groups and repositories using the following strategy:

- Single values (strings, booleans, numbers): later values override earlier ones
- Lists (topics, rulesets): merged and deduplicated
- Maps (teams, collaborators): merged with later values overriding earlier ones

#### Scenario: Topic merging

- **GIVEN** group `oss` defines `topics: ["open-source"]`
- **AND** repository defines `topics: ["terraform"]`
- **WHEN** the configuration is merged
- **THEN** the repository has topics `["open-source", "terraform"]`

#### Scenario: Team merging

- **GIVEN** group `base` defines `teams: {devops: admin}`
- **AND** repository defines `teams: {developers: push}`
- **WHEN** the configuration is merged
- **THEN** the repository has teams `{devops: admin, developers: push}`

______________________________________________________________________

### Requirement: Repository Resource Management

The system SHALL create and manage GitHub repositories using the Terraform GitHub provider.

#### Scenario: Create new repository

- **WHEN** a repository is defined in `repositories.yml` that does not exist in GitHub
- **AND** `terraform apply` is executed
- **THEN** the repository is created with the specified settings

#### Scenario: Update existing repository

- **WHEN** a repository setting is changed in configuration
- **AND** `terraform apply` is executed
- **THEN** the repository is updated to match the new configuration

#### Scenario: Repository settings applied

- **WHEN** a repository is created or updated
- **THEN** the following settings are applied: visibility, description, homepage_url, has_wiki,
  has_issues, has_projects, has_discussions, allow_merge_commit, allow_squash_merge,
  allow_rebase_merge, allow_auto_merge, allow_update_branch, delete_branch_on_merge,
  web_commit_signoff_required, vulnerability_alerts, topics, license_template

______________________________________________________________________

### Requirement: Team Access Management

The system SHALL manage team access permissions for repositories.

#### Scenario: Assign team to repository

- **GIVEN** a repository defines `teams: {devops: admin}`
- **WHEN** `terraform apply` is executed
- **THEN** the `devops` team is granted `admin` permission on the repository

#### Scenario: Update team permission

- **WHEN** a team's permission is changed from `push` to `admin`
- **AND** `terraform apply` is executed
- **THEN** the team's permission is updated

______________________________________________________________________

### Requirement: Collaborator Access Management

The system SHALL manage individual collaborator access permissions for repositories.

#### Scenario: Add collaborator to repository

- **GIVEN** a repository defines `collaborators: {username: push}`
- **WHEN** `terraform apply` is executed
- **THEN** the user `username` is granted `push` permission on the repository

______________________________________________________________________

### Requirement: Repository Rulesets

The system SHALL support repository rulesets for branch protection and policy enforcement.

#### Scenario: Apply ruleset from group

- **GIVEN** group `oss` defines `rulesets: ["main-protection"]`
- **AND** `main-protection` is defined in `rulesets.yml`
- **WHEN** a repository uses group `oss`
- **THEN** the `main-protection` ruleset is applied to the repository

#### Scenario: Ruleset with branch conditions

- **GIVEN** a ruleset targets `~DEFAULT_BRANCH`
- **WHEN** the ruleset is applied
- **THEN** the rules apply to the repository's default branch

#### Scenario: Pull request requirements

- **GIVEN** a ruleset includes a `pull_request` rule with `required_approving_review_count: 1`
- **WHEN** the ruleset is applied
- **THEN** pull requests to matching branches require at least 1 approving review

______________________________________________________________________

### Requirement: Subscription Tier Awareness

The system SHALL respect GitHub subscription tier limitations when applying rulesets.

#### Scenario: Free tier private repository

- **GIVEN** `subscription: free` is configured
- **AND** a private repository has rulesets defined
- **WHEN** Terraform is planned
- **THEN** rulesets are skipped for the private repository
- **AND** a warning is output indicating rulesets require a paid plan

#### Scenario: Paid tier private repository

- **GIVEN** `subscription: team` is configured
- **AND** a private repository has rulesets defined
- **WHEN** Terraform is planned
- **THEN** rulesets are applied to the private repository

______________________________________________________________________

### Requirement: Organization Configuration

The system SHALL read organization-level settings from `config/config.yml`.

#### Scenario: Organization name

- **WHEN** `organization: my-org` is specified in `config.yml`
- **THEN** all repositories are created in the `my-org` organization

#### Scenario: Subscription tier

- **WHEN** `subscription: free` is specified
- **THEN** the system adjusts feature availability accordingly

______________________________________________________________________

### Requirement: Output Values

The system SHALL output useful information about managed resources.

#### Scenario: Repository URLs

- **WHEN** `terraform apply` completes
- **THEN** the system outputs the URLs of all managed repositories

#### Scenario: Subscription warnings

- **WHEN** features are skipped due to subscription limitations
- **THEN** the system outputs a warning listing affected repositories
