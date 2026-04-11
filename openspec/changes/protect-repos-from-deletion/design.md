## Context

The `github_repository.this` resource in `modules/repository/main.tf` currently has
`prevent_destroy = false` in its lifecycle block, providing zero protection against accidental
repository deletion. The GitHub Terraform provider's default behavior calls `Repositories.Delete`
via the GitHub API when a resource is destroyed. Repository deletion is irreversible.

This is especially dangerous with repository partitioning (#36), where switching partitions causes
repositories to drop out of Terraform's view, triggering destroy plans for repos that still exist
and are still wanted.

Current state:
- `modules/repository/main.tf` line 38-41: `lifecycle { prevent_destroy = false }`
- No `archive_on_destroy` argument on the `github_repository` resource
- No YAML configuration option for deletion protection
- No documented decommissioning process

## Goals / Non-Goals

**Goals:**

- Prevent accidental repository deletion through Terraform lifecycle protection
- Provide a secondary safety net via `archive_on_destroy` (global default)
- Document the safe repository decommissioning workflow
- Warn users who disable safety nets via the validation script

**Non-Goals:**

- Per-repo or per-group `archive_on_destroy` override (global only for now)
- Making `prevent_destroy` configurable (Terraform limitation: must be a literal boolean)
- Protecting other resources (teams, memberships, etc.) from accidental deletion
- Implementing a "soft delete" or "decommission" workflow in Terraform itself

## Decisions

### Decision 1: Hardcode `prevent_destroy = true`

**Choice:** Set `prevent_destroy = true` as a hardcoded literal in the lifecycle block.

**Alternatives considered:**
- *Make it configurable via variable:* Not possible. Terraform requires `prevent_destroy` to be a
  literal boolean — variables, locals, and expressions are not allowed.
- *Use a separate module variant:* Would require duplicating the entire repository module with the
  only difference being the lifecycle block. Maintenance burden outweighs benefit.
- *Skip `prevent_destroy`, rely only on `archive_on_destroy`:* Weaker protection. Archived repos
  can still be permanently deleted via the API. `prevent_destroy` is a hard stop at the Terraform
  level.

**Rationale:** This is the strongest protection available. The trade-off (breaking change for
`terraform destroy` workflows) is correct — safety over convenience for an irreversible operation.

### Decision 2: Default `archive_on_destroy = true` at global level only

**Choice:** Add `archive_on_destroy` to `config/config.yml` defaults, defaulting to `true`. Pass
through to the `github_repository` resource. No group-level or repo-level override.

**Alternatives considered:**
- *Full inheritance chain (global > group > repo):* Adds complexity for a setting that should
  rarely vary. Global-only keeps it simple.
- *No `archive_on_destroy` at all:* Misses the secondary safety net for edge cases where state
  gets out of sync.

**Rationale:** `archive_on_destroy` is a safety net, not a per-repo policy decision. Global
default is sufficient. If per-repo override is needed later, the inheritance machinery already
exists and can be extended.

### Decision 3: Read from `defaults` block, not a top-level key

**Choice:** Place `archive_on_destroy` under the existing `defaults:` block in `config/config.yml`,
consistent with how other repository-level defaults are configured (`visibility`, `has_wiki`, etc.).

**Rationale:** Follows the existing pattern. Users already understand that `defaults:` contains
fallback values for repository settings.

### Decision 4: Pass as a module variable, not hardcoded

**Choice:** Add `archive_on_destroy` as a variable in `modules/repository/variables.tf` with
default `true`, and pass it from the root module.

**Rationale:** Unlike `prevent_destroy` (which must be a literal), `archive_on_destroy` is a
regular resource argument that accepts variables. This keeps the submodule reusable and testable.

## Risks / Trade-offs

**[Breaking change for destroy workflows]** Users who currently run `terraform destroy` to remove
repositories will get an error. **Mitigation:** Document the new decommissioning process in
AGENTS.md. The migration path is: `terraform state rm` the resource, then manually delete via
GitHub UI/API.

**[State surgery required for decommissioning]** `terraform state rm` is a manual, error-prone
operation. **Mitigation:** Document the exact command with examples. Consider adding a helper
script (`scripts/offboard-repos.sh`) that automates the state rm + optional manual delete.

**[`archive_on_destroy` is not perfect protection]** Archived repos can still be permanently
deleted via the GitHub API. **Mitigation:** It's a secondary net, not a primary one.
`prevent_destroy` is the primary guard. `archive_on_destroy` catches edge cases.

**[Existing state requires no migration]** Changing `prevent_destroy` from `false` to `true` does
not require a state migration. Terraform applies lifecycle rules at plan time, not at state level.
The change takes effect on the next `terraform plan` with no additional steps.
