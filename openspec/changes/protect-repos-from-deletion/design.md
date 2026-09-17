## Context

The `github_repository.this` resource in `modules/repository/main.tf` deletes repositories on destroy. The GitHub provider calls `Repositories.Delete` via the API when a resource is destroyed. Repository deletion is irreversible.

This is especially dangerous with repository partitioning (#36), where switching partitions causes repositories to drop out of Terraform's view, triggering destroy plans for repos that still exist and are still wanted.

The prior fix-partition-narrowing-destroy change already removed `prevent_destroy = true` from the module (it deadlocked normal removal and partition narrowing) and left `archive_on_destroy` unset (provider default `false` = delete).

## Goals / Non-Goals

**Goals:**

- Prevent accidental permanent repository deletion by archiving instead.
- Keep normal `for_each`-based repo removal and partition narrowing working (no plan deadlock).

**Non-Goals:**

- Making the behavior configurable (no variable, no YAML, no per-repo/group override).
- Setting `prevent_destroy` (Terraform literal-only; deadlocks removal).
- A validation warning (nothing to warn about — the value is fixed).
- Protecting other resources (teams, memberships, etc.).

## Decisions

### Decision 1: Hardcode `archive_on_destroy = true`, no configuration

**Choice:** Set `archive_on_destroy = true` directly on the `github_repository.this` resource as a fixed literal. No variable, no YAML key, no inheritance.

**Rationale:** Archiving instead of deleting is the correct default for a repository-management module — deletion is catastrophic and irreversible. Making it configurable adds a variable, a YAML defaults key, root-module wiring, and a validation warning for a value that should never sensibly be `false` in this module's use case. Hardcoding keeps the contract simple and unambiguous. `archive_on_destroy` (unlike `prevent_destroy`) is a normal resource argument, so a literal `true` works cleanly.

**How it behaves on destroy** (confirmed against provider source):

- Repo not archived: provider calls `Repositories.Edit` with `archived: true`.
- Repo already archived: no-op (provider logs and returns).
- Resource leaves Terraform state in both cases.

**Alternatives considered:**

- *Variable defaulting to `true` (global/group/repo override).* Rejected: unnecessary complexity for a value that should not vary. The inheritance machinery can be added later if a real need appears.
- *`prevent_destroy = true`.* Impossible to parameterize and deadlocks normal removal + partition narrowing.

### Decision 2: Do not set `prevent_destroy`

**Choice:** Leave `prevent_destroy` unset (default `false`).

**Rationale:** It must be a literal boolean and, when `true`, fires on every orphaned `for_each` instance whenever the resource block exists in config — turning normal YAML-entry removal and partition narrowing into permanent plan errors requiring manual `terraform state rm`. `archive_on_destroy = true` provides the actual protection without breaking those workflows.

## Risks / Trade-offs

**[Breaking change for destroy workflows]** Users who relied on `terraform destroy` or removing a YAML entry to permanently delete a repo now get an archived repo instead. **Mitigation:** Document the decommissioning process — to permanently delete, remove the repo from state after it is archived, then delete via GitHub UI/API.

**[Archived repos can still be manually deleted]** `archive_on_destroy` archives; it does not make a repo undeletable via the GitHub API/UI. This is acceptable — it protects against accidental Terraform-driven deletion, which is the threat.

**[No state migration needed]** Adding a resource argument does not require state migration. The change takes effect on the next plan/apply.
