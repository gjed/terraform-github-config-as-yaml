# Design: Add Organization Webhooks

## Overview

Add support for managing GitHub organization-level webhooks through YAML configuration. Org webhooks
are defined in `config/webhook/` (reusing existing webhook definition format) and referenced by name
from `config/config.yml`.

## Architecture

### Data Flow

```text
config/webhook/*.yml          config/config.yml
      |                              |
      v                              v
webhooks_config (existing)    org_webhooks: [name1, name2]
      |                              |
      +--------- yaml-config.tf -----+
                      |
                      v
              resolved_org_webhooks (local)
              - name lookup against webhooks_config
              - env:VAR_NAME secret resolution
                      |
                      v
              main.tf: github_organization_webhook.this
              (for_each = local.resolved_org_webhooks)
```

### Placement Decision

Org webhook **resources** are created in `main.tf` (root module), not in `modules/repository/`.
This follows the established pattern for org-level resources: `github_actions_organization_permissions`
and `github_actions_organization_workflow_permissions` are both in `main.tf`.

### Config Structure

Webhook definitions in `config/webhook/` are format-agnostic — the same definition can be referenced
by a repository, a group, or the organization. The `org_webhooks` key in `config.yml` is a simple
list of names:

```yaml
# config/config.yml
organization: my-org
subscription: free
org_webhooks:
  - audit-logger
  - ci-notifier

# config/webhook/audit.yml
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

### Resolution Logic

`yaml-config.tf` adds a new local that:

1. Reads `org_webhooks` list from `local.common_config` (defaults to `[]`)
1. Looks up each name in `local.webhooks_config` (existing map from `config/webhook/`)
1. Normalizes types (same `tostring`/`tolist`/`tobool` pattern as repo webhook resolution)
1. Resolves `env:VAR_NAME` secrets via `var.webhook_secrets` (existing variable)
1. Filters out undefined references (or fails — see design decision below)

### Organization-Only Guard

Org webhooks are guarded by `local.is_organization`. When `is_organization` is `false` (personal
account), no `github_organization_webhook` resources are created, regardless of what `org_webhooks`
contains.

### Design Decisions

**Undefined webhook reference handling**: If `org_webhooks` references a name not defined in
`config/webhook/`, the system fails at plan time with a clear error. This matches the behavior
for undefined repo webhook references (existing requirement).

**No inline definitions in config.yml**: Org webhooks must reference definitions from
`config/webhook/`. This keeps `config.yml` clean and promotes reuse. If someone needs a webhook
only for the org, they still define it in `config/webhook/` and reference it only from `org_webhooks`.

**No subscription tier gating**: The `github_organization_webhook` resource works on all GitHub
tiers. No filtering logic is needed.

## Components Changed

| File                         | Change                                                   |
| ---------------------------- | -------------------------------------------------------- |
| `yaml-config.tf`             | New locals: `org_webhook_names`, `resolved_org_webhooks` |
| `main.tf`                    | New resource: `github_organization_webhook.this`         |
| `outputs.tf`                 | New output: `org_webhooks`                               |
| `variables.tf`               | No change (reuses existing `webhook_secrets`)            |
| `config/config.yml`          | New optional key: `org_webhooks`                         |
| `scripts/validate-config.py` | Validate org webhook name references                     |
