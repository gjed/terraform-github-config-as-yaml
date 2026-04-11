## Context

The module currently manages repositories, rulesets, actions permissions, and webhooks — all scoped
to individual repositories or the organization's actions policy. There is no support for org-level
security role assignments.

GitHub's security manager role gives designated teams read access to security alerts and advisories
across all repositories in the organization. The Terraform GitHub provider offers two resources for
this:

1. `github_organization_security_manager` — **deprecated**, accepts only `team_slug`
1. `github_organization_role_team` — **replacement**, accepts `role_id` + `team_slug`, works with
   any org-level role (not just security manager)

The new resource requires looking up the `security_manager` role ID dynamically via the
`github_organization_roles` data source.

## Goals / Non-Goals

**Goals:**

- Allow users to declare security manager teams in `config/config.yml` as a simple list of team slugs
- Use the non-deprecated `github_organization_role_team` resource
- Gate the feature on `is_organization` and subscription tier (`team`/`enterprise`)
- Follow existing patterns: YAML config → locals parsing → resource creation
- Update validation script to cover the new config section

**Non-Goals:**

- Managing other org-level roles beyond `security_manager` (future work via the same resource)
- Dependabot alert/update configuration (separate feature, different resources)
- Code scanning or secret scanning custom patterns (enterprise-tier features, separate scope)
- Creating or managing the teams themselves (teams must pre-exist)

## Decisions

### 1. Use `github_organization_role_team` over deprecated resource

**Decision**: Use the newer `github_organization_role_team` resource with dynamic role ID lookup.

**Alternatives considered**:

- `github_organization_security_manager` — simpler (only needs `team_slug`), but deprecated.
  Using it means tech debt from day one and a forced migration later.

**Rationale**: The deprecated resource could be removed in any provider version bump. The newer
resource is more flexible and future-proof. The cost is one data source lookup, which is negligible.

### 2. Place security config in `config.yml` (not a separate file)

**Decision**: Add a `security` section to `config/config.yml` alongside `organization`,
`subscription`, `defaults`, and `actions`.

**Alternatives considered**:

- Separate `config/security.yml` file — would break the established single-file pattern for
  org-level config and require new file-loading logic.
- Under `defaults` — semantically wrong; security managers are an org-level concern, not a
  repository default.

**Rationale**: Org-level settings live in `config.yml`. Security manager designation is org-level.
The existing file already has `actions` as a precedent for non-repository org config.

### 3. Implement directly in `main.tf` (not a submodule)

**Decision**: Add the resources directly in `main.tf`, similar to the existing
`github_actions_organization_permissions` pattern.

**Alternatives considered**:

- New `modules/security/` submodule — overhead for what is currently two resources (one data
  source, one resource with `for_each`). Can be extracted later if security management grows.

**Rationale**: Follow the established pattern. Org-level resources in `main.tf` with config parsing
in `yaml-config.tf`. A submodule adds unnecessary indirection for a simple feature.

### 4. Gate on subscription tier in Terraform locals

**Decision**: Use a local boolean `security_managers_supported` computed from `local.subscription`
to conditionally create resources. When unsupported, resources are silently skipped (count = 0).

**Alternatives considered**:

- Terraform `check` block with warning — would emit a plan-time warning but still skip creation.
  Adds visibility but also noise for users who intentionally leave config in place while on a lower
  tier.
- Validation-only (no Terraform gate) — risky, because users who skip validation would get API
  errors.

**Rationale**: Silent skip in Terraform + warning in validation script. This matches the existing
pattern for rulesets on free tier (`local.rulesets_require_paid_for_private`).

## Risks / Trade-offs

**[Risk] Team slugs must pre-exist** → The module does not manage team creation. If a referenced
team slug doesn't exist, Terraform will fail at apply time. Mitigation: Document the dependency
clearly. The validation script can optionally warn about unverifiable team references (same as
existing team references in repository config).

**[Risk] Role ID lookup requires API access** → The `github_organization_roles` data source
makes an API call at plan time. Mitigation: Only instantiate the data source when security manager
teams are configured (conditional with `count`). One API call is well within rate limits.

**[Risk] Provider version compatibility** → `github_organization_role_team` and
`github_organization_roles` are relatively new resources. Mitigation: The module already pins
`~> 6.0`. Verify the minimum provider version that includes these resources and document it.

**[Trade-off] Silent skip vs. explicit error on wrong tier** → Chose silent skip for consistency
with rulesets behavior. Users who want visibility should run the validation script.

## Open Questions

- Should we add a `check` block (like `template_references`) that emits a warning when security
  managers are configured on an unsupported tier? This would be more visible than validation-only
  but less intrusive than an error.
