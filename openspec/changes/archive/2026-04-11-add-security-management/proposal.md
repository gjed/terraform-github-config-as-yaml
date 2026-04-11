## Why

GitHub organizations need centralized security oversight — teams designated as "security managers" get
read access to security alerts and advisories across all repositories. Currently, this module manages
repositories, rulesets, actions, and webhooks, but has no mechanism for org-level security role
assignments. Without this, users must manually configure security manager teams outside of their
GitOps workflow, creating configuration drift.

## What Changes

- Add a `security` section to `config/config.yml` for org-level security settings
- Support designating teams as security managers via `security.security_manager_teams`
- Use the `github_organization_role_team` resource (the `github_organization_security_manager`
  resource is deprecated)
- Look up the `security_manager` role ID dynamically via `github_organization_roles` data source
- Add YAML validation for the new security configuration section
- Skip security manager resources gracefully for personal accounts (`is_organization: false`)

## Capabilities

### New Capabilities

- `security-manager-teams`: Org-level security manager team designation via YAML config, using
  the `github_organization_role_team` resource with dynamic role ID lookup

### Modified Capabilities

- `repository-management`: Extend the YAML configuration schema to include a `security` section
  in `config.yml` alongside existing `organization`, `subscription`, `defaults`, and `actions`

## Impact

- **New Terraform resources**: `github_organization_role_team` (one per security manager team),
  `github_organization_roles` data source (one lookup)
- **Config schema**: New optional `security` block in `config/config.yml`
- **Validation script**: `scripts/validate-config.py` needs updated schema rules
- **Dependencies**: Referenced teams must exist before being assigned as security managers — same
  constraint that already applies to team assignments on repositories
- **Subscription tiers**: Security manager roles are available on Team and Enterprise plans. Free
  and Pro plans do not support org-level security manager designation. The implementation should
  gate on subscription tier to avoid API errors.
