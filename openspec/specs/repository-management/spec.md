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
`repository/`, `ruleset/`, `webhook/`, and `membership/` containing `*.yml` files.

Split configuration applies to: `repository`, `group`, `ruleset`, and `membership` types. These
MUST be defined in directories using singular naming convention: `<config_path>/repository/`,
`<config_path>/group/`, `<config_path>/ruleset/`, `<config_path>/membership/`.

Organization-level settings (`<config_path>/config.yml`) remain a single file and do not support
splitting. The common configuration file SHALL support an optional `security` section for
organization-level security settings. The system SHALL also read the `org_webhooks` list from
`config/config.yml` to resolve organization-level webhook references.

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

#### Scenario: Load org webhooks from config.yml

- **WHEN** Terraform is initialized and planned
- **THEN** the system reads the `org_webhooks` list from `config/config.yml`
- **AND** defaults to an empty list if the key is absent

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

#### Scenario: Load membership configuration from directory

- **GIVEN** a `<config_path>/membership/` directory exists with files `engineering.yml` and
  `leadership.yml`
- **WHEN** Terraform is initialized and planned
- **THEN** the system reads all `.yml` files from the `membership/` directory
- **AND** merges them alphabetically into a single membership configuration map

#### Scenario: Load branch protection configuration from directory

- **GIVEN** a `config/branch-protection/` directory exists with `.yml` files
- **WHEN** Terraform is initialized and planned
- **THEN** the system reads all `.yml` files from the directory
- **AND** merges them alphabetically into a single branch protections definition map

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

#### Scenario: Missing membership directory is not an error

- **GIVEN** a `<config_path>/membership/` directory does not exist
- **WHEN** Terraform is initialized and planned
- **THEN** the system uses an empty membership map
- **AND** no error is raised (membership directory is optional)

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

______________________________________________________________________

### Requirement: Configuration Merging Strategy

The system SHALL merge configurations from groups and repositories using the following strategy:

- Single values (strings, booleans, numbers): later values override earlier ones
- Lists (topics, rulesets, branch_protections): merged and deduplicated
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

#### Scenario: Branch protection merging

- **GIVEN** group `base` defines `branch_protections: ["main-protection"]`
- **AND** repository defines `branch_protections: ["release-protection"]`
- **WHEN** the configuration is merged
- **THEN** the repository has branch protections `["main-protection", "release-protection"]`

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
Repository rulesets are limited to definitions with `scope: repository` or no `scope` field.
Definitions with `scope: organization` are excluded from the per-repository rulesets map and are
not available for assignment via `rulesets:` in groups or repositories. Attempting to reference an
org-scoped ruleset per-repository is a misconfiguration.

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

#### Scenario: Org-scoped ruleset excluded from per-repository rulesets

- **GIVEN** `config/ruleset/` contains a ruleset with `scope: organization`
- **AND** another ruleset with no `scope` field (repo-scoped)
- **WHEN** Terraform parses the configuration
- **THEN** only the repo-scoped ruleset is available for assignment via `rulesets:` in groups/repos
- **AND** the org-scoped ruleset is not included in the per-repository rulesets map

______________________________________________________________________

### Requirement: Subscription Tier Awareness

The system SHALL respect GitHub subscription tier limitations when applying rulesets.

The system SHALL skip organization-level rulesets (`scope: organization`) on `free` and `pro`
plans, and SHALL emit a `skipped_org_rulesets` output listing the names of skipped org rulesets.
Organization rulesets require a `team` or `enterprise` subscription.

The existing behaviour for repository-level rulesets on private repos is unchanged: on `free`
plans, rulesets are skipped for private repos and listed in `subscription_warnings`.

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

#### Scenario: Free tier — org rulesets skipped with output

- **GIVEN** `subscription: free` is configured in `config.yml`
- **AND** at least one org ruleset (`scope: organization`) is defined
- **WHEN** `terraform plan` is executed
- **THEN** no `github_organization_ruleset` resources are planned
- **AND** the `skipped_org_rulesets` output contains the names of the skipped org rulesets

#### Scenario: Pro tier — org rulesets skipped

- **GIVEN** `subscription: pro` is configured
- **AND** at least one org ruleset is defined
- **WHEN** `terraform plan` is executed
- **THEN** no `github_organization_ruleset` resources are planned

#### Scenario: Team tier — org rulesets applied

- **GIVEN** `subscription: team` is configured
- **AND** at least one org ruleset is defined
- **WHEN** `terraform apply` is executed
- **THEN** `github_organization_ruleset` resources are created for all org rulesets
- **AND** `skipped_org_rulesets` output is null

#### Scenario: Enterprise tier — org rulesets applied

- **GIVEN** `subscription: enterprise` is configured
- **WHEN** `terraform apply` is executed
- **THEN** all org rulesets are created without restriction

______________________________________________________________________

### Requirement: Organization Rulesets

The system SHALL support organization-level rulesets that apply rules across multiple repositories
based on repository name patterns, using `github_organization_ruleset`.

See the `org-ruleset-management` spec for full scenarios.

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

______________________________________________________________________

### Requirement: Output Values

The system SHALL output useful information about managed resources.

#### Scenario: Repository URLs

- **WHEN** `terraform apply` completes
- **THEN** the system outputs the URLs of all managed repositories

#### Scenario: Subscription warnings

- **WHEN** features are skipped due to subscription limitations
- **THEN** the system outputs a warning listing affected repositories

#### Scenario: Duplicate branch protection key warning

- **WHEN** two files in `config/branch-protection/` both define `main-protection`
- **AND** `terraform apply` completes
- **THEN** the `duplicate_config_keys` output includes the branch protection duplicate with
  the affected file names

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

______________________________________________________________________

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

### Requirement: Organization Webhook Configuration

The system SHALL support organization-level webhook configuration by referencing webhook names
defined in `config/webhook/` from the `org_webhooks` list in `config/config.yml`. Organization
webhooks fire for events across all repositories in the organization.

#### Scenario: Define org webhooks by name reference

- **GIVEN** a webhook `audit-logger` is defined in `config/webhook/audit.yml`:
  ```yaml
  audit-logger:
    url: https://audit.example.com/github
    content_type: json
    secret: env:ORG_WEBHOOK_SECRET
    events:
      - repository
      - member
      - team
      - organization
    active: true
  ```
- **AND** `config/config.yml` contains:
  ```yaml
  org_webhooks:
    - audit-logger
  ```
- **WHEN** `terraform apply` is executed
- **THEN** a `github_organization_webhook` resource is created
- **AND** the webhook URL is `https://audit.example.com/github`
- **AND** the webhook triggers on repository, member, team, and organization events

#### Scenario: Multiple org webhooks

- **GIVEN** `config/config.yml` defines:
  ```yaml
  org_webhooks:
    - audit-logger
    - ci-notifier
  ```
- **AND** both `audit-logger` and `ci-notifier` are defined in `config/webhook/`
- **WHEN** `terraform apply` is executed
- **THEN** two `github_organization_webhook` resources are created
- **AND** each uses the settings from its respective webhook definition

#### Scenario: Org webhook with secret resolution

- **GIVEN** a webhook defines `secret: env:ORG_WEBHOOK_SECRET`
- **AND** `var.webhook_secrets` contains `{ ORG_WEBHOOK_SECRET = "supersecret" }` <!-- pragma: allowlist secret -->
- **WHEN** `terraform apply` is executed
- **THEN** the org webhook is created with the resolved secret value
- **AND** the secret is marked as sensitive in Terraform state

#### Scenario: Org webhook without secret

- **GIVEN** a webhook is defined without a `secret` field
- **AND** the webhook is referenced in `org_webhooks`
- **WHEN** `terraform apply` is executed
- **THEN** the org webhook is created without a secret

#### Scenario: Org webhook default values

- **GIVEN** an org webhook is defined with only required fields:
  ```yaml
  minimal-webhook:
    url: https://example.com/hook
    events:
      - push
  ```
- **WHEN** `terraform apply` is executed
- **THEN** the webhook uses `content_type: json` by default
- **AND** the webhook is active by default
- **AND** SSL verification is enabled by default

#### Scenario: No org webhooks configured

- **GIVEN** `config/config.yml` does not contain an `org_webhooks` key
- **WHEN** `terraform apply` is executed
- **THEN** no `github_organization_webhook` resources are created

#### Scenario: Empty org webhooks list

- **GIVEN** `config/config.yml` contains `org_webhooks: []`
- **WHEN** `terraform apply` is executed
- **THEN** no `github_organization_webhook` resources are created

#### Scenario: Reference undefined webhook in org_webhooks

- **GIVEN** `config/config.yml` references `org_webhooks: ["nonexistent-webhook"]`
- **AND** no webhook named `nonexistent-webhook` is defined in `config/webhook/`
- **WHEN** `terraform plan` is executed
- **THEN** Terraform fails with an error indicating the webhook is not defined

#### Scenario: Personal account skips org webhooks

- **GIVEN** `config/config.yml` contains `is_organization: false`
- **AND** `org_webhooks` is configured with valid webhook references
- **WHEN** `terraform apply` is executed
- **THEN** no `github_organization_webhook` resources are created

______________________________________________________________________

### Requirement: Organization Webhook Resource Management

The system SHALL create, update, and delete `github_organization_webhook` resources based on the
resolved org webhook configuration.

#### Scenario: Create org webhook

- **GIVEN** an org webhook is configured and does not exist in GitHub
- **WHEN** `terraform apply` is executed
- **THEN** the `github_organization_webhook` resource is created
- **AND** the configuration block includes url, content_type, secret, and insecure_ssl
- **AND** the events list is applied
- **AND** the active flag is applied

#### Scenario: Update org webhook

- **GIVEN** an existing org webhook's URL is changed in `config/webhook/`
- **WHEN** `terraform apply` is executed
- **THEN** the `github_organization_webhook` resource is updated with the new URL

#### Scenario: Remove org webhook

- **GIVEN** an org webhook name is removed from the `org_webhooks` list in `config/config.yml`
- **WHEN** `terraform apply` is executed
- **THEN** the corresponding `github_organization_webhook` resource is destroyed

#### Scenario: Shared webhook definition update

- **GIVEN** a webhook definition in `config/webhook/` is referenced by both a repository and
  `org_webhooks`
- **AND** the URL is changed in the webhook definition
- **WHEN** `terraform apply` is executed
- **THEN** both the repository webhook and the organization webhook are updated
