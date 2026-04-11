# Change: Add Organization Settings Management

Resolves: [#28](https://github.com/gjed/terraform-github-config-as-yaml/issues/28)

## Why

Organization-level settings — member privileges, security policies, repository defaults — are currently
managed manually via the GitHub UI. This creates an auditability gap: settings can drift without a
code-reviewed paper trail. Codifying them in the same YAML-first workflow used for repositories brings
org governance under the same GitOps discipline.

## What Changes

- Extend `config/config.yml` with an optional `settings:` block for `github_organization_settings`
- Create a `github_organization_settings` resource in `main.tf`, gated on `is_organization: true`
- Apply feature-gating for GHAS settings that require Enterprise subscription
- Emit a human-readable warning when GHAS or other enterprise-only settings are configured on lower tiers
- Document the 2FA enforcement risk prominently (immediately removes members without 2FA)

## Supported Settings

| YAML Key                                                       | Terraform Attribute                                            | Notes                                      |
| -------------------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------ |
| `default_repository_permission`                                | `default_repository_permission`                                | `none`/`read`/`write`/`admin`              |
| `members_can_create_repositories`                              | `members_can_create_repositories`                              | bool                                       |
| `members_can_create_public_repositories`                       | `members_can_create_public_repositories`                       | bool                                       |
| `members_can_create_private_repositories`                      | `members_can_create_private_repositories`                      | bool                                       |
| `members_can_create_internal_repositories`                     | `members_can_create_internal_repositories`                     | enterprise only                            |
| `members_can_fork_private_repositories`                        | `members_can_fork_private_repositories`                        | bool                                       |
| `web_commit_signoff_required`                                  | `web_commit_signoff_required`                                  | bool                                       |
| `two_factor_requirement`                                       | `two_factor_requirement`                                       | ⚠️ removes members without 2FA immediately |
| `dependabot_alerts_enabled_for_new_repositories`               | `dependabot_alerts_enabled_for_new_repositories`               | bool                                       |
| `dependabot_security_updates_enabled_for_new_repositories`     | `dependabot_security_updates_enabled_for_new_repositories`     | bool                                       |
| `dependency_graph_enabled_for_new_repositories`                | `dependency_graph_enabled_for_new_repositories`                | bool                                       |
| `secret_scanning_enabled_for_new_repositories`                 | `secret_scanning_enabled_for_new_repositories`                 | GHAS/Enterprise                            |
| `secret_scanning_push_protection_enabled_for_new_repositories` | `secret_scanning_push_protection_enabled_for_new_repositories` | GHAS/Enterprise                            |
| `advanced_security_enabled_for_new_repositories`               | `advanced_security_enabled_for_new_repositories`               | GHAS/Enterprise                            |
| `blog`                                                         | `blog`                                                         | string                                     |
| `company`                                                      | `company`                                                      | string                                     |
| `description`                                                  | `description`                                                  | string                                     |
| `email`                                                        | `email`                                                        | string                                     |
| `location`                                                     | `location`                                                     | string                                     |

## Subscription / GHAS Gating

Settings that only work on Enterprise (GHAS features) are silently ignored on lower tiers and emit a
`subscription_warnings` entry. The resource is omitted entirely when `is_organization: false`.

## Impact

- Affected specs: `repository-management`
- Affected code: `yaml-config.tf` (parse `settings:` from `config.yml`), `main.tf` (new resource),
  `outputs.tf` (add `organization_settings_warnings`)
- Backward compatible: `settings:` block is optional; existing configs require no changes
