# Change: Add Organization Membership Management

Resolves: [#35](https://github.com/gjed/terraform-github-config-as-yaml/issues/35)

## Why

Organization membership is currently managed manually through the GitHub UI or invitations. This
means there is no audit trail, onboarding and offboarding are ad-hoc, and configuration drift is
undetectable. Codifying membership in YAML alongside repository configuration brings the same
GitOps benefits the module already provides for repositories: traceability, review workflows, and
drift prevention.

## What Changes

- Add a new `config/membership/` directory with YAML files defining organization members and their
  roles (`member` or `admin`)
- Add YAML parsing logic in `yaml-config.tf` to load and merge membership configuration files
  (following the same split-file pattern as `repository/`, `group/`, and `ruleset/`)
- Add `github_membership` resources in `main.tf` to manage organization members
- Add a safety mechanism (opt-in flag or `lifecycle { prevent_destroy }`) to prevent accidental
  member removal — removing a user from YAML should not silently remove them from the org
- Add validation in `scripts/validate-config.py` for membership configuration
- Skip membership management for personal accounts (`is_organization: false`)
- Add module outputs for managed membership (member count, member list)

## What Does NOT Change

- Repository-level collaborator management (`github_repository_collaborator`) remains unchanged and
  continues to be configured per-repo via `collaborators:` in repository/group config
- Outside collaborator tracking is NOT in scope — this focuses on `github_membership` only
- Organization invitations (`github_organization_invitation`) are NOT managed — Terraform's
  `github_membership` handles the invite-or-add workflow internally
- User blocking (`github_organization_block`) is NOT in scope for this change

## Capabilities

### New Capabilities

- `org-membership`: Organization membership management via YAML configuration, including member/admin
  role assignment, safety mechanisms for destructive operations, and personal account exclusion.

### Modified Capabilities

- `module-interface`: New `membership_management_enabled` variable and membership-related outputs
  (member count, member list).
- `repository-management`: YAML parsing section updated to document the new `membership/` config
  directory alongside existing `repository/`, `group/`, `ruleset/`, and `webhook/` directories.

## Impact

- **New config directory:** `config/membership/` (follows existing split-file pattern)
- **Affected code:**
  - `yaml-config.tf` — new locals for membership parsing
  - `main.tf` — new `github_membership` resource block
  - `variables.tf` — new `membership_management_enabled` variable (opt-in safety)
  - `outputs.tf` — new membership outputs
  - `scripts/validate-config.py` — membership config validation
- **Risk:** This is a **high-risk** feature. Removing a user from YAML triggers org removal, which
  revokes access to all private repos and destroys private forks. The safety mechanism is critical.
- **Conflict with IdP/SCIM:** If the org uses SCIM/SSO provisioning for membership, this feature
  MUST NOT be used. This must be documented prominently.
- **Subscription:** `github_membership` works on all tiers that support organizations. Personal
  accounts are excluded via the existing `is_organization` flag.
