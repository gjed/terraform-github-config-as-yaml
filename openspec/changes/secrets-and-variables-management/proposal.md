## Why

Secrets and variables for GitHub Actions and Dependabot are currently unmanaged by this module,
forcing users to configure them manually or via separate tooling. This breaks the GitOps promise
of the module — you can manage repos, rulesets, webhooks, teams, and membership as YAML, but
secrets and variables remain a manual gap. Adding them completes the configuration surface and
improves auditability.

## What Changes

- Add **organization-level** secrets and variables management:
  - Actions secrets (`github_actions_organization_secret`)
  - Actions variables (`github_actions_organization_variable`)
  - Dependabot secrets (`github_dependabot_organization_secret`)
- Add **repository-level** secrets and variables management:
  - Actions secrets (`github_actions_secret`)
  - Actions variables (`github_actions_variable`)
  - Dependabot secrets (`github_dependabot_secret`)
- New YAML config directory `config/secret/` for org-level secret/variable definitions
- New `secrets` and `variables` keys in group and repository YAML configs
- New Terraform input variable `secret_values` (sensitive map) for passing actual secret values
  into the module (same `env:VAR_NAME` pattern as `webhook_secrets`)
- Group inheritance support: secrets and variables defined in groups are inherited by repositories,
  with repo-level overrides (consistent with existing merge behavior for teams, webhooks, etc.)
- Validation for undefined secret references and missing `env:` values

## Capabilities

### New Capabilities

- `org-secrets-and-variables`: Organization-level Actions secrets, Actions variables, and
  Dependabot secrets — defined in `config/secret/` and referenced from `config/config.yml`,
  with visibility scoping (all, private, selected repositories).
- `repo-secrets-and-variables`: Repository-level Actions secrets, Actions variables, and
  Dependabot secrets — defined in groups and/or individual repository configs, with group
  inheritance and repo-level override support.

### Modified Capabilities

(none)

## Impact

- **New Terraform resources:** 6 new resource types across org and repo levels
- **New config directory:** `config/secret/` for organization-level definitions
- **New input variable:** `secret_values` (sensitive `map(string)`) — mirrors `webhook_secrets`
- **YAML schema changes:** New `secrets` and `variables` keys in group and repository configs
- **State sensitivity:** Secret values will be stored in Terraform state — documentation must
  emphasize encrypted remote backends
- **yaml-config.tf:** New locals for loading `config/secret/`, merging group-level
  secrets/variables, and resolving `env:VAR_NAME` references
- **modules/repository/:** New variables and resources for repo-level secrets/variables
- **validate-config.py:** New validation rules for secret/variable schema
- **No breaking changes** — all new config keys are optional with empty defaults
