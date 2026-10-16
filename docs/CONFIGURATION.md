# Configuration Reference

This document describes all supported configuration keys for `config/config.yml`,
`config/group/`, `config/repository/`, and `config/ruleset/`.

______________________________________________________________________

## `config/config.yml`

### Top-level keys

| Key               | Type   | Default  | Description                                                    |
| ----------------- | ------ | -------- | -------------------------------------------------------------- |
| `organization`    | string | required | GitHub organization name or username                           |
| `subscription`    | string | `free`   | GitHub subscription tier (`free`, `pro`, `team`, `enterprise`) |
| `is_organization` | bool   | `true`   | Whether the owner is an org (vs. a personal account)           |

______________________________________________________________________

## Organization Settings (`settings:`)

The optional `settings:` block in `config/config.yml` manages the
`github_organization_settings` resource. It is only applied when
`is_organization: true` (the default).

When the `settings:` block is absent no org-settings resource is created —
existing organization settings are left untouched.

### Profile fields

| YAML Key        | Type   | Default  | Description                                   |
| --------------- | ------ | -------- | --------------------------------------------- |
| `billing_email` | string | required | Billing contact email (required by provider)  |
| `company`       | string | `null`   | Company name shown on the org profile         |
| `blog`          | string | `null`   | Website URL shown on the org profile          |
| `email`         | string | `null`   | Public contact email shown on the org profile |
| `location`      | string | `null`   | Location shown on the org profile             |
| `description`   | string | `null`   | Short description shown on the org profile    |

### Member privileges

| YAML Key                                  | Type   | Default | Description                                                   |
| ----------------------------------------- | ------ | ------- | ------------------------------------------------------------- |
| `default_repository_permission`           | string | `read`  | Base permission for members: `none`, `read`, `write`, `admin` |
| `members_can_create_repositories`         | bool   | `true`  | Allow members to create repositories                          |
| `members_can_create_public_repositories`  | bool   | `true`  | Allow members to create public repositories                   |
| `members_can_create_private_repositories` | bool   | `true`  | Allow members to create private repositories                  |
| `members_can_fork_private_repositories`   | bool   | `false` | Allow members to fork private repositories                    |
| `web_commit_signoff_required`             | bool   | `false` | Require web commit signoff on all commits                     |

### Two-factor authentication

> [!WARNING]
> **`two_factor_requirement: true` immediately removes all organization members
> who do not have two-factor authentication enabled.** There is no grace period.
> Removed members lose access to all private repositories instantly.
> Enable this only after verifying that all members have 2FA configured.

*Note: `two_factor_requirement` is not currently exposed as a Terraform
attribute by the GitHub provider (`integrations/github >= 6.12.0`). Manage it
via the GitHub organization security settings UI.*

### Dependabot and dependency graph

These settings are available on all subscription tiers.

| YAML Key                                                   | Type | Default | Description                                             |
| ---------------------------------------------------------- | ---- | ------- | ------------------------------------------------------- |
| `dependabot_alerts_enabled_for_new_repositories`           | bool | `false` | Enable Dependabot alerts for new repositories           |
| `dependabot_security_updates_enabled_for_new_repositories` | bool | `false` | Enable Dependabot security updates for new repositories |
| `dependency_graph_enabled_for_new_repositories`            | bool | `false` | Enable the dependency graph for new repositories        |

### Enterprise-only settings (GHAS)

> [!IMPORTANT]
> The following settings require a **GitHub Enterprise** subscription
> (`subscription: enterprise` in `config/config.yml`). On lower tiers they are
> silently skipped and an `organization_settings_warnings` output is emitted.

| YAML Key                                                       | Type | Default | Description                                                |
| -------------------------------------------------------------- | ---- | ------- | ---------------------------------------------------------- |
| `advanced_security_enabled_for_new_repositories`               | bool | `false` | Enable GitHub Advanced Security for new repositories       |
| `secret_scanning_enabled_for_new_repositories`                 | bool | `false` | Enable secret scanning for new repositories                |
| `secret_scanning_push_protection_enabled_for_new_repositories` | bool | `false` | Enable secret scanning push protection for new repos       |
| `members_can_create_internal_repositories`                     | bool | `false` | Allow members to create internal repositories (Enterprise) |

### Example

```yaml
settings:
  billing_email: billing@example.com
  company: "ACME Corp"
  blog: "https://acme.example.com"
  description: "ACME GitHub organization"

  default_repository_permission: read
  members_can_create_repositories: true
  members_can_create_public_repositories: false
  members_can_create_private_repositories: true
  members_can_fork_private_repositories: false
  web_commit_signoff_required: true

  dependabot_alerts_enabled_for_new_repositories: true
  dependabot_security_updates_enabled_for_new_repositories: true
  dependency_graph_enabled_for_new_repositories: true

  # Enterprise only — skipped with a warning on lower tiers
  advanced_security_enabled_for_new_repositories: true
  secret_scanning_enabled_for_new_repositories: true
  secret_scanning_push_protection_enabled_for_new_repositories: true
  members_can_create_internal_repositories: false
```

______________________________________________________________________

## Organization Actions (`actions:`)

The optional `actions:` block in `config/config.yml` manages
`github_actions_organization_permissions` and
`github_actions_organization_workflow_permissions`.

| YAML Key                           | Type   | Default | Description                                                |
| ---------------------------------- | ------ | ------- | ---------------------------------------------------------- |
| `enabled_repositories`             | string | `all`   | Which repos can use Actions: `all`, `none`, `selected`     |
| `allowed_actions`                  | string | `all`   | Which actions are allowed: `all`, `local_only`, `selected` |
| `default_workflow_permissions`     | string | `read`  | Default `GITHUB_TOKEN` permissions: `read`, `write`        |
| `can_approve_pull_request_reviews` | bool   | `false` | Whether Actions can approve pull request reviews           |

When `allowed_actions: selected`, add an `allowed_actions_config:` sub-block:

| YAML Key               | Type         | Default | Description                           |
| ---------------------- | ------------ | ------- | ------------------------------------- |
| `github_owned_allowed` | bool         | `true`  | Allow actions in `github/*` namespace |
| `verified_allowed`     | bool         | `true`  | Allow verified Marketplace actions    |
| `patterns_allowed`     | list(string) | `[]`    | Explicit action patterns to allow     |

______________________________________________________________________

## Group and repository keys

Only the keys listed in `VALID_GROUP_KEYS` and `VALID_REPOSITORY_KEYS` in `scripts/validate-config.py` are read
from `config/group/` and `config/repository/` entries. Any other key is silently dropped by Terraform;
`validate-config.py` reports it as a warning.

### Linear history is branch-level only

GitHub has no repository-wide linear-history setting, so there is no `require_linear_history` group or repository
key. Enforce it on specific branches with a `required_linear_history` rule in a ruleset (see
`config/ruleset/default-rulesets.yml`) or `required_linear_history: true` in a branch protection (see
`config/branch-protection/`).

______________________________________________________________________

## Secrets and variables

Actions secrets, Actions variables, and Dependabot secrets are managed at two levels. Neither level is gated by
`subscription` in this module, but on GitHub Free organization-level secrets and variables are not accessible from
private repositories.

- **Organization level:** `config/secret/*.yml`, one or more files, each with optional `actions_secrets`,
  `actions_variables`, and `dependabot_secrets` maps. Visibility is `all`, `private`, or `selected`.
  `selected_repositories` lists managed repository names and is only used with `visibility: selected`.
  Files merge per type by name, last file wins; duplicates appear in `duplicate_key_warnings`. Organization
  resources are skipped when `is_organization: false`.
- **Repository level:** `secrets.actions`, `secrets.dependabot`, and `variables.actions` under a group or
  repository. Groups apply in order and a repository entry replaces a group entry with the same name.

Secret values are never written in YAML. A secret's `value` must be `env:VAR_NAME`, and the value comes from
the sensitive `secret_values` Terraform variable:

```hcl
module "github_org" {
  # ...
  secret_values = {
    DEPLOY_TOKEN = var.deploy_token
  }
}
```

Variable values are plaintext. YAML numbers and booleans are converted to strings.

Names must match `^[A-Z_][A-Z0-9_]*$` and must not start with `GITHUB_`. Lowercase names are rejected because
GitHub upper-cases them, which would cause a perpetual diff.

The plan fails when a secret references a missing `secret_values` key, when a name is invalid, when a
`selected_repositories` entry is not a managed repository, or when visibility is not one of the allowed values.
Error messages name the secret and the reference, never the value.

> **Warning: state contains secret values.** Terraform stores secret values in its state file. Use an
> encrypted remote backend with restricted access, for example an S3 bucket with SSE-KMS, or Terraform Cloud.
> Do not commit a local `terraform.tfstate` that contains these resources.

Each secret and variable is one GitHub API call. Organizations with hundreds of them may hit API rate limits on
the first apply. Use `terraform apply -parallelism=N` to limit concurrency.

```yaml
# config/secret/org-secrets.yml
actions_secrets:
  DEPLOY_TOKEN:
    value: "env:DEPLOY_TOKEN"
    visibility: selected
    selected_repositories: [my-app, my-api]
actions_variables:
  ENVIRONMENT:
    value: "production"
    visibility: all
dependabot_secrets:
  REGISTRY_PASSWORD:
    value: "env:REGISTRY_PASSWORD"
    visibility: private
```

______________________________________________________________________

## Subscription tier feature matrix

| Feature                   | free | pro | team | enterprise |
| ------------------------- | :--: | :-: | :--: | :--------: |
| Rulesets on public repos  |  ✓   |  ✓  |  ✓   |     ✓      |
| Rulesets on private repos |      |  ✓  |  ✓   |     ✓      |
| Organization settings     |  ✓   |  ✓  |  ✓   |     ✓      |
| GHAS / secret scanning    |      |     |      |     ✓      |
| Internal repositories     |      |     |      |     ✓      |
