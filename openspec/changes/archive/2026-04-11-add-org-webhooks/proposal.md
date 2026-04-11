# Change: Add Organization Webhooks

## Why

The module currently supports repository-level webhooks via `github_repository_webhook`, but GitHub
also supports organization-level webhooks via `github_organization_webhook`. Org webhooks fire for
events across **all** repositories in the organization, making them essential for:

- Centralized audit logging across the entire org
- Organization-wide CI/CD event notifications
- Security monitoring (member changes, team changes, repo creation)
- Compliance event tracking

Without org webhook support, users must either configure the same webhook on every repository
individually or manage org webhooks outside of Terraform entirely.

## What Changes

- **NEW**: Organization webhook support via `github_organization_webhook` resource
- **MODIFIED**: `config.yml` gains an `org_webhooks` key that references webhook definitions by name
- **MODIFIED**: `yaml-config.tf` resolves org webhook references from `config/webhook/` definitions
- **MODIFIED**: `main.tf` creates org webhook resources (parallel to org Actions permissions)
- **MODIFIED**: Module outputs include org webhook information

## Impact

- Affected specs: `repository-management` (new org webhook configuration and resource), `module-interface` (new output)
- Affected code:
  - `config/config.yml` schema — new `org_webhooks` list field
  - `yaml-config.tf` — org webhook resolution logic
  - `main.tf` — `github_organization_webhook` resource block
  - `outputs.tf` — org webhook output
  - `scripts/validate-config.py` — validation for org webhook references

## Dependencies

None. This change reuses existing webhook definition infrastructure (`config/webhook/` directory,
`var.webhook_secrets`, `env:VAR_NAME` secret resolution pattern).

## References

- GitHub Issue: #30
