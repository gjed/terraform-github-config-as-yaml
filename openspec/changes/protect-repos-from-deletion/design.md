## Context

The `github_repository.this` resource in `modules/repository/main.tf` deletes repositories on
destroy. The GitHub provider calls `Repositories.Delete` via the API when a resource is destroyed.
Repository deletion is irreversible, and nothing in the module stands between a removed YAML entry and
a permanent delete.

`prevent_destroy` has never been `true` in shipped code: `modules/repository/main.tf` has carried
`prevent_destroy = false` (no protection) since the first commit. The prior
fix-partition-narrowing-destroy change dropped `prevent_destroy = true` from the *proposed* design —
it deadlocked normal removal — and left `archive_on_destroy` unset (provider default `false` =
delete).

## Goals / Non-Goals

**Goals:**

- Prevent accidental permanent repository deletion by archiving instead.
- Keep normal `for_each`-based repo removal working (no plan deadlock).

**Non-Goals:**

- Setting `prevent_destroy` (Terraform literal-only; deadlocks removal).
- A YAML config key or per-repo/group override (the variable exists for the e2e fixture, not for
  consumer tuning).
- Protecting other resources (teams, memberships, etc.).

## Decisions

### Decision 1: `archive_on_destroy` variable defaulting to `true`

**Choice:** Add an `archive_on_destroy` variable to the repository module and the root module,
defaulting to `true`, and pass it to the `github_repository.this` resource. No YAML key, no
per-repo/group inheritance.

**Rationale:** Archiving instead of deleting is the correct default for a repository-management
module — deletion is catastrophic and irreversible. A variable (rather than a bare literal) is
required so the e2e test fixture can set `archive_on_destroy = false` and hard-delete its throwaway
repos on teardown; without it, `make destroy` would archive every `e2e-*` repo, the names would stay
taken, and the next apply would collide with `422 name already exists`. The default stays `true` so
every production consumer is protected by default. Scope is deliberately limited to a single
module/root variable — no YAML surface, no group/repo override — because the value should not vary per
repository in normal use.

**How it behaves on destroy** (confirmed against provider source):

- Repo not archived: provider calls `Repositories.Edit` with `archived: true`.
- Repo already archived: no-op (provider logs and returns).
- `archive_on_destroy = false`: provider calls `Repositories.Delete` (permanent).
- Resource leaves Terraform state in all cases.

**Alternatives considered:**

- *Hardcoded literal `true`, no variable.* Rejected: leaves the e2e fixture archiving throwaway
  repos, breaking the fixture's destroy contract and the local test loop.
- *Full YAML inheritance (global > group > repo).* Rejected: unnecessary complexity for a value that
  should not vary per repo. Can be added later if a real need appears.
- *`prevent_destroy = true`.* Impossible to parameterize and deadlocks normal removal.

### Decision 2: Do not set `prevent_destroy`

**Choice:** Leave `prevent_destroy` unset (default `false`).

**Rationale:** It must be a literal boolean and, when `true`, fires on every orphaned `for_each`
instance whenever the resource block exists in config — turning normal YAML-entry removal into
permanent plan errors requiring manual `terraform state rm`. `archive_on_destroy = true` provides the
actual protection without breaking those workflows.

### Decision 3: e2e fixture opts out

**Choice:** `tests/e2e/main.tf` sets `archive_on_destroy = false`.

**Rationale:** The e2e fixture provisions throwaway `e2e-*` repos and asserts (in
`openspec/specs/e2e-test-fixture/spec.md`) that `terraform destroy` leaves no orphans. Archiving would
leave the names taken and break the next apply. The fixture is the one place a hard delete is correct.

## Risks / Trade-offs

**[Breaking change for destroy workflows]** Users who relied on `terraform destroy` or removing a YAML
entry to permanently delete a repo now get an archived repo instead. **Mitigation:** Document the
decommissioning process — to permanently delete, remove the repo from state after it is archived, then
delete via GitHub UI/API.

**[Archived repos can still be manually deleted]** `archive_on_destroy` archives; it does not make a
repo undeletable via the GitHub API/UI. This is acceptable — it protects against accidental
Terraform-driven deletion, which is the threat.

**[No state migration needed]** Adding a resource argument does not require state migration. The change
takes effect on the next plan/apply.
