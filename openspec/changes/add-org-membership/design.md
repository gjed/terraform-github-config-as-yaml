# Design: Add Organization Membership Management

## Context

The module currently manages GitHub repositories, rulesets, Actions permissions, and webhooks via
YAML configuration. Organization membership (who belongs to the org and with what role) is managed
manually through the GitHub UI. This creates a gap: repository access is codified, but the people
who have access are not.

The Terraform GitHub provider offers `github_membership` which manages the member/admin role for a
user in an organization. This resource is inherently destructive — removing a membership entry
triggers org removal, which revokes private repo access and destroys private forks.

The module already handles split-file YAML loading for `repository/`, `group/`, `ruleset/`, and
`webhook/` directories. Membership follows the same pattern but is simpler (flat list, no
inheritance or merging needed).

## Goals / Non-Goals

**Goals:**

- Manage organization membership (member/admin roles) via YAML configuration
- Follow existing module patterns (split-file YAML, `yaml-config.tf` parsing, resource in `main.tf`)
- Provide safety mechanisms to prevent accidental org member removal
- Support only organizations (skip silently for personal accounts)
- Provide clear documentation about SCIM/SSO conflicts

**Non-Goals:**

- Outside collaborator management at the org level (already per-repo via `collaborators:`)
- Organization invitations as a separate resource (provider handles this internally)
- User blocking (`github_organization_block`) — separate feature
- Team membership — separate from org membership, different resource
- Integration with SCIM/IdP — this is a manual YAML approach, not an IdP sync

## Decisions

### 1. Config location: `config/membership/` directory

**Decision:** Use a new `config/membership/` directory with split-file support, matching the
existing pattern for `repository/`, `group/`, and `ruleset/`.

**Rationale:** Follows the established convention. Users can split members by team, department, or
any other grouping across multiple YAML files.

**Alternative considered:** Adding membership to `config/config.yml` — rejected because it breaks
the pattern where config.yml only holds organization-level settings and defaults, not resource
definitions. Membership lists can grow large and benefit from split-file organization.

### 2. YAML structure: flat map of username → role

**Decision:** Use a simple map where keys are GitHub usernames and values are role strings.

```yaml
# config/membership/engineering.yml
developer1: member
developer2: member
team-lead: admin
```

**Rationale:** This is the simplest possible structure that maps directly to the
`github_membership` resource (which takes `username` and `role`). No nesting, no inheritance needed.

**Alternative considered:** Array of objects with `username` and `role` fields — rejected because
it adds verbosity without benefit, and maps naturally prevent duplicate usernames within a file
(duplicate detection across files uses the existing pattern).

### 3. Safety mechanism: opt-in via variable

**Decision:** Add a `membership_management_enabled` boolean variable that defaults to `false`.
Membership resources are only created when this variable is explicitly set to `true`.

**Rationale:** This is the simplest and most Terraform-idiomatic approach. It prevents accidents
during initial setup (membership config files can exist without effect until explicitly enabled).
The `lifecycle { prevent_destroy }` alternative was rejected because it makes intentional removals
impossible without `terraform state rm` workarounds, which is worse operationally.

**Alternative considered:** `lifecycle { prevent_destroy }` on membership resources — rejected
because it makes intentional removal a two-step process requiring state manipulation. A boolean
toggle is clearer: if it's off, no membership is managed. If it's on, the YAML is the source of
truth.

### 4. Personal account handling: skip silently

**Decision:** When `is_organization: false` in `config/config.yml`, membership resources are not
created regardless of the `membership_management_enabled` variable.

**Rationale:** `github_membership` requires an organization. Personal accounts don't have members.
Skipping silently (not erroring) matches how the module handles other org-only features.

### 5. No group inheritance for membership

**Decision:** Membership is defined only in `config/membership/` files. It does not participate in
the group/repository configuration inheritance system.

**Rationale:** Membership is orthogonal to repository configuration. A user's org membership
role is independent of which repos they can access. Mixing these concepts would add complexity
without value.

### 6. Missing directory handling: optional

**Decision:** The `config/membership/` directory is optional. If it doesn't exist, no membership
resources are created (same pattern as `webhook/`).

**Rationale:** Not all consumers want to manage membership. Making the directory optional ensures
the module works without it and doesn't break existing setups when upgrading.

## Risks / Trade-offs

**[Accidental member removal] → Opt-in variable.** Even with the opt-in toggle, a user who
removes a username from YAML and runs `terraform apply` will remove that person from the org.
The plan output will show the destruction, and `terraform plan` should always be reviewed. The
opt-in variable prevents "I added the config directory and now Terraform wants to remove everyone
not listed."

**[SCIM/SSO conflict] → Documentation only.** If an org uses SCIM for membership provisioning,
Terraform and SCIM will fight over membership state. There is no programmatic way to detect this.
The documentation must warn prominently, and the validation script should print a reminder when
membership config is present.

**[API rate limits with large orgs] → Acceptable.** Each membership is one API call. Even a
500-person org is well within the 5000 req/hr limit. No batching needed.

**[Terraform state sensitivity] → Minimal.** `github_membership` stores username and role — no
secrets. State sensitivity is low compared to webhook secrets.

**[Role granularity] → GitHub limitation.** GitHub only supports `member` and `admin` roles at the
org level. This is a platform constraint, not a design choice. Finer-grained access is managed
through teams (separate feature).
