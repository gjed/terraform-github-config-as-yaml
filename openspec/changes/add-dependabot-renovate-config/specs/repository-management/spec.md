## ADDED Requirements

### Requirement: Dependabot Configuration Management

The system SHALL support generating and provisioning Dependabot configuration files based on YAML
configuration.

#### Scenario: Basic Dependabot configuration

- **GIVEN** a repository defines:
  ```yaml
  dependabot:
    updates:
      - package_ecosystem: npm
        directory: "/"
        schedule:
          interval: weekly
  ```
- **WHEN** `terraform apply` is executed
- **THEN** a `.github/dependabot.yml` file is provisioned to the provisioning branch
- **AND** the file contains valid Dependabot v2 configuration

#### Scenario: Multiple package ecosystems

- **GIVEN** a repository defines multiple `updates` entries for npm, docker, and github-actions
- **WHEN** the configuration is generated
- **THEN** all ecosystems are included in the single `dependabot.yml` file

#### Scenario: Dependabot with reviewers and labels

- **GIVEN** a repository defines:
  ```yaml
  dependabot:
    updates:
      - package_ecosystem: npm
        directory: "/"
        schedule:
          interval: weekly
        reviewers:
          - security-team
        labels:
          - dependencies
          - automated
  ```
- **WHEN** the configuration is generated
- **THEN** the `dependabot.yml` includes reviewers and labels configuration

#### Scenario: Dependabot grouped updates

- **GIVEN** a repository defines `groups` within an update entry
- **WHEN** the configuration is generated
- **THEN** the groups are included in the Dependabot configuration
- **AND** dependency grouping is applied according to patterns

#### Scenario: Dependabot commit message prefix

- **GIVEN** a repository defines:
  ```yaml
  dependabot:
    updates:
      - package_ecosystem: npm
        commit_message:
          prefix: "chore(deps)"
  ```
- **WHEN** the configuration is generated
- **THEN** the commit message configuration is included

______________________________________________________________________

### Requirement: Renovate Configuration Management

The system SHALL support generating and provisioning Renovate configuration files based on YAML
configuration.

#### Scenario: Basic Renovate configuration

- **GIVEN** a repository defines:
  ```yaml
  renovate:
    extends:
      - "config:recommended"
    schedule:
      - "before 6am on monday"
  ```
- **WHEN** `terraform apply` is executed
- **THEN** a `renovate.json` file is provisioned to the provisioning branch
- **AND** the file contains valid Renovate configuration

#### Scenario: Renovate with automerge

- **GIVEN** a repository defines:
  ```yaml
  renovate:
    extends:
      - "config:recommended"
    automerge: true
    automergeType: pr
    platformAutomerge: true
  ```
- **WHEN** the configuration is generated
- **THEN** the automerge settings are included in `renovate.json`

#### Scenario: Renovate package rules

- **GIVEN** a repository defines `packageRules` with matchers and settings
- **WHEN** the configuration is generated
- **THEN** the package rules are included in Renovate configuration
- **AND** the rules are applied in order

#### Scenario: Renovate preset extensions

- **GIVEN** a repository defines `extends: ["config:recommended", "group:allNonMajor"]`
- **WHEN** the configuration is generated
- **THEN** the extends array is preserved in the output

#### Scenario: Renovate configuration location

- **GIVEN** a repository defines `renovate.config_file: ".github/renovate.json"`
- **WHEN** the configuration is generated
- **THEN** the file is provisioned to `.github/renovate.json` instead of the root

______________________________________________________________________

### Requirement: Dependency Update Configuration Groups

The system SHALL support configuration groups for shared dependency update policies.

#### Scenario: Group with Dependabot configuration

- **GIVEN** a group `use-dependabot` defines:
  ```yaml
  dependabot:
    updates:
      - package_ecosystem: npm
        directory: "/"
        schedule:
          interval: weekly
  ```
- **AND** a repository specifies `groups: ["use-dependabot"]`
- **WHEN** `terraform apply` is executed
- **THEN** the repository inherits the Dependabot configuration from the group

#### Scenario: Group with Renovate configuration

- **GIVEN** a group `use-renovate` defines Renovate configuration
- **AND** a repository specifies `groups: ["use-renovate"]`
- **WHEN** `terraform apply` is executed
- **THEN** the repository inherits the Renovate configuration from the group

#### Scenario: Repository overrides group dependency config

- **GIVEN** a group defines `dependabot.updates[].schedule.interval: weekly`
- **AND** a repository overrides with `dependabot.updates[].schedule.interval: daily`
- **WHEN** the configuration is merged
- **THEN** the repository-level schedule takes precedence

______________________________________________________________________

### Requirement: Dependency Update Merging Strategy

The system SHALL merge dependency update configurations following the established merging strategy.

#### Scenario: Merge Dependabot updates from multiple groups

- **GIVEN** group `base` defines updates for `npm`
- **AND** group `ci` defines updates for `github-actions`
- **AND** a repository uses both groups
- **WHEN** the configuration is merged
- **THEN** both update entries are included in `dependabot.yml`

#### Scenario: Merge Renovate packageRules

- **GIVEN** a group defines package rules for dev dependencies
- **AND** a repository defines additional package rules for specific packages
- **WHEN** the configuration is merged
- **THEN** both sets of rules are included in order (group first, then repository)

#### Scenario: Conflict resolution for same ecosystem

- **GIVEN** a group defines `npm` updates with `interval: weekly`
- **AND** a repository defines `npm` updates with `interval: daily`
- **WHEN** the configuration is merged
- **THEN** the repository configuration completely replaces the group's `npm` entry

______________________________________________________________________

### Requirement: Dual Tool Support

The system SHALL support using both Dependabot and Renovate in the same organization with different
repositories.

#### Scenario: Different tools per repository

- **GIVEN** repository `legacy-app` uses group `use-dependabot`
- **AND** repository `new-app` uses group `use-renovate`
- **WHEN** `terraform apply` is executed
- **THEN** `legacy-app` gets `dependabot.yml`
- **AND** `new-app` gets `renovate.json`
- **AND** neither repository gets the other tool's config

#### Scenario: Prevent dual configuration on same repository

- **GIVEN** a repository defines both `dependabot` and `renovate` configuration
- **WHEN** `terraform validate` is executed
- **THEN** a warning is emitted about potential conflicts
- **AND** both configurations are generated (user intentionally wants both)

______________________________________________________________________

### Requirement: Dependency Configuration Validation

The system SHALL validate dependency update configurations before provisioning.

#### Scenario: Invalid Dependabot ecosystem

- **GIVEN** a repository defines `package_ecosystem: invalid`
- **WHEN** `terraform validate` is executed
- **THEN** an error is raised indicating the invalid ecosystem

#### Scenario: Invalid schedule interval

- **GIVEN** a repository defines `schedule.interval: yearly`
- **WHEN** `terraform validate` is executed
- **THEN** an error is raised indicating valid intervals are: daily, weekly, monthly

#### Scenario: Missing required fields

- **GIVEN** a Dependabot update entry is missing `package_ecosystem` or `directory`
- **WHEN** `terraform validate` is executed
- **THEN** an error is raised indicating the missing required field

______________________________________________________________________

### Requirement: Dependency Configuration Presets

The system SHALL support predefined presets for common dependency update scenarios.

#### Scenario: Use preset for npm project

- **GIVEN** a repository defines `dependabot: { preset: "npm-weekly" }`
- **WHEN** the configuration is expanded
- **THEN** the preset is expanded to a full Dependabot configuration
- **AND** includes npm ecosystem with weekly updates

#### Scenario: Preset with overrides

- **GIVEN** a repository defines:
  ```yaml
  dependabot:
    preset: "npm-weekly"
    updates:
      - package_ecosystem: npm
        schedule:
          interval: daily  # Override preset
  ```
- **WHEN** the configuration is merged
- **THEN** the override takes precedence over the preset default

#### Scenario: List available presets

- **GIVEN** presets are defined in configuration or templates
- **WHEN** documentation is generated
- **THEN** available presets and their defaults are documented
