## Context

The module provides a complete GitOps workflow for GitHub repository management but requires teams
to exist before they can be referenced in repository configurations. Users must create teams manually
or via separate Terraform code, breaking the single-source-of-truth model.

**Stakeholders:**

- Organization administrators who manage team structures
- DevOps teams maintaining Terraform configurations
- Template users who want full GitHub org management from YAML

## Goals / Non-Goals

**Goals:**

- Define teams, membership, and settings in YAML following existing config patterns
- Support nested team hierarchies (up to 3 levels) with visually intuitive nesting syntax
- Manage team membership (members and maintainers) directly
- Configure PR review request delegation per team
- Validate team configuration at plan time and via the validation script
- Keep team management decoupled from repo-team assignments

**Non-Goals:**

- Changing how repos/groups reference teams (stays as `teams: {slug: permission}`)
- Automatic repo-team wiring from team definitions
- LDAP DN mapping (Enterprise-only feature, future addition)
- SCIM/SSO-aware membership management (document caveat for template users)

## Decisions

### Decision: Separate concerns — teams and repo assignments are independent

**What:** Team definitions in `config/team/` manage team creation, membership, and settings.
Repository team assignments in `config/repository/` and `config/group/` remain unchanged.

**Why:** This matches the module's existing architecture where repos reference external resources
by name. It allows incremental adoption — users can manage teams without changing repo configs,
and repos can still reference teams managed outside the module.

**Alternatives considered:**

- **Integrated reference**: Team definitions automatically wire up repo access. Rejected because
  it introduces bidirectional config flow (teams → repos and repos → teams), conflicts with the
  existing unidirectional model, and creates merge complexity when both sides declare access.

### Decision: Nested YAML syntax for parent/child teams

**What:** Child teams are defined under their parent's `teams` key, creating a visually nested
hierarchy in YAML.

```yaml
engineering:
  description: "Engineering org"
  teams:
    platform-team:
      description: "Platform engineering"
      teams:
        platform-sre:
          description: "SRE sub-team"
```

**Why:** The hierarchy is immediately visible in the YAML structure. Parent-child relationships
are implicit from nesting, eliminating dangling parent references entirely. A flat list with
`parent_team: engineering` string references would require cross-reference validation and is
harder to read.

**Trade-off:** Teams in the same hierarchy must be in the same file. This is acceptable because
teams are typically organized by org unit (one file per top-level team).

**Alternatives considered:**

- **Flat list with `parent_team` string reference**: Simpler Terraform locals but worse UX,
  requires explicit validation for dangling references and cycles.

### Decision: Tiered module invocations for dependency ordering

**What:** Teams are classified into tiers (0, 1, 2) based on nesting depth. Three separate
module calls in `main.tf` create teams tier by tier, with each tier referencing the previous
tier's outputs for `parent_team_id`.

```hcl
module "teams_root" {
  source   = "./modules/team"
  for_each = local.tier_0_teams
}

module "teams_level_1" {
  source         = "./modules/team"
  for_each       = local.tier_1_teams
  parent_team_id = module.teams_root[each.value.parent_team].team_id
}

module "teams_level_2" {
  source         = "./modules/team"
  for_each       = local.tier_2_teams
  parent_team_id = module.teams_level_1[each.value.parent_team].team_id
}
```

**Why:** Terraform's `for_each` does not support dynamic dependency ordering. Fixed resource
tiers let Terraform's dependency graph naturally order creation: tier 0 → tier 1 → tier 2.

**Alternatives considered:**

- **Single module with internal tier logic**: The module can't reference its own outputs for
  parent IDs across `for_each` iterations. Terraform doesn't support self-referencing resources
  within the same `for_each`.

### Decision: Membership always managed when declared

**What:** If `members` or `maintainers` lists are present in the YAML, they are managed by
Terraform. No opt-in toggle.

**Why:** The primary use case is orgs without SCIM/SSO that need team membership codified. Adding
a `manage_members` toggle adds complexity for a problem the target users don't have. The SCIM/SSO
caveat is documented for template users.

### Decision: Organization-only guard

**What:** Team resources are only created when `is_organization: true` in `config.yml`. Personal
accounts skip team management entirely.

**Why:** GitHub Teams are an organization feature. The `github_team` resource fails on personal
accounts. This matches how `github_actions_organization_permissions` is already guarded.

## Architecture

### YAML Configuration Schema

Teams are defined in `config/team/*.yml` following the split-directory pattern.

```yaml
# config/team/engineering.yml
engineering:
  description: "Engineering org"
  privacy: closed
  members:
    - dev1
    - dev2
  maintainers:
    - eng-lead
  review_request_delegation:
    enabled: true
    algorithm: round_robin
    member_count: 2
    notify: true
  teams:
    platform-team:
      description: "Platform engineering"
      privacy: closed
      members:
        - user1
        - user2
      maintainers:
        - lead1
      teams:
        platform-sre:
          description: "SRE sub-team"
          members:
            - sre1
            - sre2
    frontend-team:
      description: "Frontend engineering"
      members:
        - fe1
        - fe2
```

**Field reference:**

| Field                                    | Type   | Required | Default       | Description                                  |
| ---------------------------------------- | ------ | -------- | ------------- | -------------------------------------------- |
| `description`                            | string | yes      | —             | Team description                             |
| `privacy`                                | string | no       | `closed`      | `closed` or `secret`                         |
| `members`                                | list   | no       | `[]`          | GitHub usernames with member role            |
| `maintainers`                            | list   | no       | `[]`          | GitHub usernames with maintainer role        |
| `review_request_delegation`              | object | no       | `null`        | PR review delegation settings                |
| `review_request_delegation.enabled`      | bool   | yes      | —             | Enable/disable delegation                    |
| `review_request_delegation.algorithm`    | string | no       | `round_robin` | `round_robin` or `load_balance`              |
| `review_request_delegation.member_count` | int    | no       | `1`           | Number of members to assign                  |
| `review_request_delegation.notify`       | bool   | no       | `true`        | Notify the whole team                        |
| `teams`                                  | map    | no       | `{}`          | Nested child teams (recursive, max 3 levels) |

### Config Loading and Flattening (`yaml-config.tf`)

1. **Load**: Read `config/team/*.yml` files, merge alphabetically (same as repos/groups/rulesets).
   The team directory is optional — if absent, an empty map is used (same as webhooks, unlike
   repositories/groups/rulesets which require their directories to exist)
1. **Flatten**: Walk the nested `teams` structure recursively, producing a flat map of all teams
   with computed fields:
   - `slug` — the team's key name
   - `parent_slug` — the parent team's key (null for root teams)
   - `tier` — 0, 1, or 2 based on nesting depth
   - All declared fields (description, privacy, members, maintainers, review_request_delegation)
1. **Classify**: Split flat map into `tier_0_teams`, `tier_1_teams`, `tier_2_teams`
1. **Validate**: Check block rejects teams nested deeper than 3 levels

### Module: `modules/team/`

Single module used for all tiers. Accepts one team definition and creates:

- `github_team` — team resource
- `github_team_membership` — one per member + one per maintainer
- `github_team_settings` — if `review_request_delegation` is provided

**Variables:**

- `name` (string) — Team name/slug
- `description` (string) — Team description
- `privacy` (string) — closed or secret
- `parent_team_id` (string, optional) — Parent team ID from previous tier
- `members` (list) — Member usernames
- `maintainers` (list) — Maintainer usernames
- `review_request_delegation` (object, optional) — Delegation settings

**Outputs:**

- `team_id` — The team's ID (used by child tiers for `parent_team_id`)
- `team_slug` — The team's slug

### Main Module Wiring (`main.tf`)

Three module blocks, one per tier:

```hcl
module "teams_root" {
  source   = "./modules/team"
  for_each = local.is_organization ? local.tier_0_teams : {}
  ...
}

module "teams_level_1" {
  source         = "./modules/team"
  for_each       = local.is_organization ? local.tier_1_teams : {}
  parent_team_id = module.teams_root[each.value.parent_slug].team_id
  ...
}

module "teams_level_2" {
  source         = "./modules/team"
  for_each       = local.is_organization ? local.tier_2_teams : {}
  parent_team_id = module.teams_level_1[each.value.parent_slug].team_id
  ...
}
```

### Validation

**Terraform check blocks:**

- Parent references resolve (implicit from nesting — no dangling refs possible)
- No teams nested deeper than 3 levels
- No duplicate team slugs across the flattened map

**`validate-config.py` extensions:**

- Team YAML schema validation (required fields, valid privacy values)
- Depth limit check (max 3 levels)
- Duplicate slug detection across files
- Warning when a repo/group references a team slug not defined in `config/team/`

### Outputs (`outputs.tf`)

- `managed_teams` — Map of team slug → team ID for all managed teams
- `team_membership` — Summary of team membership for reference

## Risks / Trade-offs

| Risk                                         | Mitigation                                                                    |
| -------------------------------------------- | ----------------------------------------------------------------------------- |
| SCIM/SSO conflict with membership management | Document caveat prominently; users with SCIM should not use membership fields |
| Nested YAML limits file splitting            | One file per top-level team is the natural org unit anyway                    |
| 3-tier limit may not cover all orgs          | Covers virtually all real org structures; document the limit                  |
| Team slug uniqueness across nesting levels   | Validate at plan time and in validation script                                |
| Renaming a team requires state surgery       | Document as known limitation of Terraform GitHub provider                     |

## Migration Plan

1. **Phase 1**: Add `config/team/` directory, `yaml-config.tf` loading and flattening logic,
   `modules/team/` submodule, tier-0 module wiring — supports flat (non-nested) teams
1. **Phase 2**: Add tier-1 and tier-2 module wiring, nesting support in flattening logic
1. **Phase 3**: Add `github_team_settings` support, validation script extensions, documentation
1. **Rollback**: Remove `config/team/` directory and team module blocks. No impact on existing
   repo configurations.

## Open Questions

None — all questions resolved during design.
