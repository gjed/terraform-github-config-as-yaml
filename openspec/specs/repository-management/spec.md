# repository-management Specification

## Purpose

Define the requirements for managing GitHub repositories as code using Terraform. This spec covers
YAML-based configuration, configuration groups with inheritance, repository resource management, team and
collaborator access, rulesets for branch protection, and subscription tier awareness.

## Requirements

### Requirement: YAML-Based Repository Configuration

The system SHALL read repository configurations from YAML files under the directory specified by
`var.config_path` using Terraform's native `yamldecode()` function. The default consumer layout
expected under `config_path` is: `config.yml` at the root, and sub-directories `group/`,
`repository/`, `ruleset/`, and `webhook/` containing `*.yml` files.

Split configuration applies to: `repository`, `group`, and `ruleset` types only. These MUST be
defined in directories using singular naming convention: `<config_path>/repository/`,
`<config_path>/group/`, `<config_path>/ruleset/`.

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

#### Scenario: Single file not supported for splittable types

- **GIVEN** only `<config_path>/repositories.yml` exists (no `<config_path>/repository/` directory)
- **WHEN** Terraform is initialized and planned
- **THEN** Terraform fails with an error indicating directory structure is required

#### Scenario: Consumer specifies custom config directory

- **WHEN** a consumer sets `config_path = "${path.root}/my-configs"`
- **THEN** the module reads YAML from `my-configs/` instead of any hardcoded path

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

---

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

---

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

---

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

---

### Requirement: Collaborator Access Management

The system SHALL manage individual collaborator access permissions for repositories.

#### Scenario: Add collaborator to repository

- **GIVEN** a repository defines `collaborators: {username: push}`
- **WHEN** `terraform apply` is executed
- **THEN** the user `username` is granted `push` permission on the repository

---

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

---

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

---

### Requirement: Organization Configuration

The system SHALL read organization-level settings from `config/config.yml`.

#### Scenario: Organization name

- **WHEN** `organization: my-org` is specified in `config.yml`
- **THEN** all repositories are created in the `my-org` organization

#### Scenario: Subscription tier

- **WHEN** `subscription: free` is specified
- **THEN** the system adjusts feature availability accordingly

---

### Requirement: Output Values

The system SHALL output useful information about managed resources.

#### Scenario: Repository URLs

- **WHEN** `terraform apply` completes
- **THEN** the system outputs the URLs of all managed repositories

#### Scenario: Subscription warnings

- **WHEN** features are skipped due to subscription limitations
- **THEN** the system outputs a warning listing affected repositories

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

---

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

---

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

---

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

### Requirement: Webhook Definitions

The system SHALL support webhook definitions in the `config/webhook/` directory. Each webhook is defined
by name and can be referenced in groups or repositories.

#### Scenario: Load webhook definitions from directory

- **GIVEN** a `config/webhook/` directory exists with files `ci.yml` and `notifications.yml`
- **WHEN** Terraform is initialized and planned
- **THEN** the system reads all `.yml` files from the `config/webhook/` directory
- **AND** merges them alphabetically into a single webhooks definition map

#### Scenario: Webhook definition structure

- **GIVEN** a webhook is defined in `config/webhook/ci.yml`:
  ```yaml
  jenkins-ci:
    url: https://jenkins.example.com/github-webhook/
    content_type: json
    secret: env:JENKINS_WEBHOOK_SECRET
    events:
      - push
      - pull_request
    active: true
  ```
- **WHEN** Terraform parses the configuration
- **THEN** the webhook is available to reference by name `jenkins-ci`

#### Scenario: Empty webhook directory

- **GIVEN** a `config/webhook/` directory exists but contains no `.yml` files
- **WHEN** Terraform is initialized and planned
- **THEN** the system uses an empty webhook definitions map

#### Scenario: Missing webhook directory

- **GIVEN** a `config/webhook/` directory does not exist
- **WHEN** Terraform is initialized and planned
- **THEN** the system uses an empty webhook definitions map
- **AND** no error is raised (webhooks are optional)

______________________________________________________________________

### Requirement: Webhook Configuration

The system SHALL support repository webhook configuration by referencing webhook names defined in
`config/webhook/` or by inline definition. Webhooks can be assigned at the group or repository level.

#### Scenario: Reference webhook by name in repository

- **GIVEN** a webhook `jenkins-ci` is defined in `config/webhook/ci.yml`
- **AND** a repository references webhooks in `config/repository/my-repo.yml`:
  ```yaml
  my-repo:
    webhooks:
      - jenkins-ci
  ```
- **WHEN** `terraform apply` is executed
- **THEN** the `jenkins-ci` webhook is created on the repository

#### Scenario: Inline webhook definition in repository

- **GIVEN** a repository defines an inline webhook in `config/repository/my-repo.yml`:
  ```yaml
  my-repo:
    webhooks:
      - name: custom-webhook
        url: https://custom.example.com/webhook
        events: [push]
  ```
- **WHEN** `terraform apply` is executed
- **THEN** the webhook is created on the repository with the specified URL and events

#### Scenario: Webhook with all options

- **GIVEN** a webhook is defined with all configuration options:
  ```yaml
  webhooks:
    - name: full-webhook
      url: https://example.com/hook
      content_type: json
      secret: env:WEBHOOK_SECRET
      events: [push, pull_request, release]
      active: true
      insecure_ssl: false
  ```
- **WHEN** `terraform apply` is executed
- **THEN** the webhook is created with content type `application/json`
- **AND** the secret is read from the `WEBHOOK_SECRET` environment variable
- **AND** the webhook triggers on push, pull_request, and release events
- **AND** the webhook is active
- **AND** SSL verification is enabled

#### Scenario: Webhook default values

- **GIVEN** a webhook is defined with only required fields:
  ```yaml
  webhooks:
    - name: minimal-webhook
      url: https://example.com/hook
      events: [push]
  ```
- **WHEN** `terraform apply` is executed
- **THEN** the webhook uses `content_type: json` by default
- **AND** the webhook is active by default
- **AND** SSL verification is enabled by default

______________________________________________________________________

### Requirement: Webhook Inheritance from Groups

The system SHALL support webhook inheritance from configuration groups with merge-by-name semantics.

#### Scenario: Reference webhook by name in group

- **GIVEN** a webhook `ci-pipeline` is defined in `config/webhook/ci.yml`
- **AND** group `with-ci` references webhooks in `config/group/with-ci.yml`:
  ```yaml
  with-ci:
    webhooks:
      - ci-pipeline
  ```
- **AND** a repository uses group `with-ci`
- **WHEN** `terraform apply` is executed
- **THEN** the `ci-pipeline` webhook is created on the repository

#### Scenario: Inline webhook definition in group

- **GIVEN** group `with-ci` defines an inline webhook:
  ```yaml
  with-ci:
    webhooks:
      - name: ci-pipeline
        url: https://ci.example.com/webhook
        events: [push, pull_request]
  ```
- **AND** a repository uses group `with-ci`
- **WHEN** `terraform apply` is executed
- **THEN** the `ci-pipeline` webhook is created on the repository

#### Scenario: Repository webhook overrides group webhook

- **GIVEN** group `with-ci` references webhook `ci-pipeline`
- **AND** the repository also references or defines a webhook named `ci-pipeline` with different settings
- **WHEN** the configuration is merged
- **THEN** the repository's webhook definition completely overrides the group's webhook

#### Scenario: Combine group and repository webhooks

- **GIVEN** group `with-ci` references webhook `ci-pipeline`
- **AND** the repository references webhook `slack-notify`
- **WHEN** the configuration is merged
- **THEN** both `ci-pipeline` and `slack-notify` webhooks are created on the repository

#### Scenario: Multiple groups with webhooks

- **GIVEN** group `with-ci` references webhook `ci-pipeline`
- **AND** group `with-notifications` references webhook `slack-notify`
- **AND** a repository uses groups `["with-ci", "with-notifications"]`
- **WHEN** the configuration is merged
- **THEN** both webhooks are created on the repository

#### Scenario: Later group overrides earlier group webhook

- **GIVEN** group `base` references webhook `ci-pipeline` with URL `https://old-ci.example.com`
- **AND** group `modern` references webhook `ci-pipeline` with URL `https://new-ci.example.com`
- **AND** a repository uses groups `["base", "modern"]`
- **WHEN** the configuration is merged
- **THEN** the `ci-pipeline` webhook uses URL `https://new-ci.example.com`

#### Scenario: Reference undefined webhook

- **GIVEN** a repository references webhook `undefined-webhook`
- **AND** no webhook named `undefined-webhook` is defined in `config/webhook/`
- **WHEN** `terraform plan` is executed
- **THEN** Terraform fails with an error indicating the webhook is not defined

______________________________________________________________________

### Requirement: Webhook Secret Handling

The system SHALL securely handle webhook secrets through environment variable references.

#### Scenario: Secret from environment variable

- **GIVEN** a webhook defines `secret: env:MY_WEBHOOK_SECRET`
- **AND** environment variable `MY_WEBHOOK_SECRET` is set to `supersecret123`
- **WHEN** `terraform apply` is executed
- **THEN** the webhook is created with secret `supersecret123`
- **AND** the secret is marked as sensitive in Terraform

#### Scenario: Missing environment variable

- **GIVEN** a webhook defines `secret: env:MISSING_VAR`
- **AND** environment variable `MISSING_VAR` is not set
- **WHEN** `terraform plan` is executed
- **THEN** Terraform fails with an error indicating the missing environment variable

#### Scenario: Webhook without secret

- **GIVEN** a webhook is defined without a `secret` field
- **WHEN** `terraform apply` is executed
- **THEN** the webhook is created without a secret
