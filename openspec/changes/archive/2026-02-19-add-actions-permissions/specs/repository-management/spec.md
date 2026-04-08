# repository-management Spec Delta

## ADDED Requirements

### Requirement: Repository Actions Permissions

The system SHALL manage GitHub Actions permissions for repositories through YAML configuration.

#### Scenario: Enable Actions with default settings

- **GIVEN** a repository is defined without an `actions` block
- **WHEN** `terraform apply` is executed
- **THEN** no `github_actions_repository_permissions` resource is created
- **AND** the repository uses GitHub's default Actions settings

#### Scenario: Configure allowed actions policy

- **GIVEN** a repository defines `actions.allowed_actions: selected`
- **AND** `actions.allowed_actions_config.github_owned_allowed: true`
- **AND** `actions.allowed_actions_config.patterns_allowed: ["myorg/*"]`
- **WHEN** `terraform apply` is executed
- **THEN** a `github_actions_repository_permissions` resource is created
- **AND** only GitHub-owned actions and actions matching `myorg/*` are allowed

#### Scenario: Configure workflow permissions

- **GIVEN** a repository defines `actions.default_workflow_permissions: read`
- **AND** `actions.can_approve_pull_request_reviews: false`
- **WHEN** `terraform apply` is executed
- **THEN** workflows receive read-only `GITHUB_TOKEN` permissions by default
- **AND** workflows cannot approve pull request reviews

#### Scenario: Disable Actions for repository

- **GIVEN** a repository defines `actions.enabled: false`
- **WHEN** `terraform apply` is executed
- **THEN** GitHub Actions is disabled for that repository

______________________________________________________________________

### Requirement: Organization Actions Permissions

The system SHALL support organization-level GitHub Actions permissions in `config.yml`.

#### Scenario: Configure organization-wide Actions policy

- **GIVEN** `config.yml` defines `organization.actions.allowed_actions: selected`
- **AND** `organization.actions.default_workflow_permissions: read`
- **WHEN** `terraform apply` is executed
- **THEN** a `github_actions_organization_permissions` resource is created
- **AND** organization-wide defaults are applied

#### Scenario: Restrict which repositories can use Actions

- **GIVEN** `config.yml` defines `organization.actions.enabled_repositories: selected`
- **WHEN** `terraform apply` is executed
- **THEN** only explicitly enabled repositories can use GitHub Actions

#### Scenario: Skip organization Actions when not configured

- **GIVEN** `config.yml` does not define an `organization.actions` block
- **WHEN** `terraform apply` is executed
- **THEN** no `github_actions_organization_permissions` resource is created

______________________________________________________________________

### Requirement: Actions Configuration Inheritance

The system SHALL support Actions configuration inheritance from configuration groups.

#### Scenario: Inherit Actions settings from group

- **GIVEN** group `secure-defaults` defines `actions.allowed_actions: selected`
- **AND** repository `my-repo` uses `groups: ["secure-defaults"]`
- **AND** `my-repo` does not define its own `actions` block
- **WHEN** the configuration is merged
- **THEN** `my-repo` inherits `allowed_actions: selected` from the group

#### Scenario: Override group Actions settings

- **GIVEN** group `base` defines `actions.default_workflow_permissions: read`
- **AND** repository `my-repo` defines `actions.default_workflow_permissions: write`
- **WHEN** the configuration is merged
- **THEN** `my-repo` uses `default_workflow_permissions: write`

#### Scenario: Merge allowed actions patterns

- **GIVEN** group `base` defines `actions.allowed_actions_config.patterns_allowed: ["actions/*"]`
- **AND** repository defines `actions.allowed_actions_config.patterns_allowed: ["myorg/*"]`
- **WHEN** the configuration is merged
- **THEN** the repository has `patterns_allowed: ["actions/*", "myorg/*"]`

______________________________________________________________________

### Requirement: Actions Secure Defaults

The system SHALL apply secure defaults when Actions configuration is partially specified.

#### Scenario: Default workflow permissions

- **GIVEN** a repository defines `actions.allowed_actions: selected`
- **AND** does not specify `default_workflow_permissions`
- **WHEN** the configuration is resolved
- **THEN** `default_workflow_permissions` defaults to `read`

#### Scenario: Default PR approval setting

- **GIVEN** a repository defines an `actions` block
- **AND** does not specify `can_approve_pull_request_reviews`
- **WHEN** the configuration is resolved
- **THEN** `can_approve_pull_request_reviews` defaults to `false`
