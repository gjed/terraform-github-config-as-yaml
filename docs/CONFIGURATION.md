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
attribute by the GitHub provider (`integrations/github ~> 6.0`). Manage it
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

## Subscription tier feature matrix

| Feature                   | free | pro | team | enterprise |
| ------------------------- | :--: | :-: | :--: | :--------: |
| Rulesets on public repos  |  ✓   |  ✓  |  ✓   |     ✓      |
| Rulesets on private repos |      |  ✓  |  ✓   |     ✓      |
| Organization settings     |  ✓   |  ✓  |  ✓   |     ✓      |
| GHAS / secret scanning    |      |     |      |     ✓      |
| Internal repositories     |      |     |      |     ✓      |
