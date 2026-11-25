## Why

The `github_repository` resource deletes repositories when they are removed from configuration or
state. Deleting a GitHub repository is catastrophic and irreversible, and nothing in the module
currently stands between a dropped YAML entry and a permanent delete.

`prevent_destroy` cannot solve this: Terraform requires it to be a literal boolean (no
variables/expressions), and setting it `true` deadlocks the module's normal `for_each`-based repo
removal — every orphaned instance trips a permanent plan error. It has been `prevent_destroy = false`
(no protection) since the first commit.

## What Changes

- **BREAKING:** Add an `archive_on_destroy` variable defaulting to `true` and pass it to the
  `github_repository` resource. On destroy, the GitHub provider archives the repository (via the edit
  API, `archived: true`) instead of permanently deleting it. Previously repos were deleted on destroy
  (`archive_on_destroy` defaulted to `false`).
- The variable exists so the e2e test fixture can set `archive_on_destroy = false` and hard-delete
  its throwaway repos on teardown. Production consumers should leave the default.
- `prevent_destroy` is intentionally not set.
- Document the safe repository decommissioning process and the archive-on-destroy behavior.

## Capabilities

### New Capabilities

- `deletion-protection`: Repositories are archived instead of deleted on destroy via
  `archive_on_destroy`, defaulting to `true`. Covers the Terraform resource lifecycle, the variable,
  and the documented decommissioning process.

### Modified Capabilities

- `repository-management`: `archive_on_destroy` (default `true`) is applied to the repository
  resource.

## Impact

- `modules/repository/main.tf` — `archive_on_destroy = var.archive_on_destroy`, `prevent_destroy`
  line removed
- `modules/repository/variables.tf` — new `archive_on_destroy` variable (default `true`)
- `variables.tf` — new root `archive_on_destroy` variable (default `true`)
- `main.tf` — pass `archive_on_destroy` to the repository module
- `tests/e2e/main.tf` — fixture sets `archive_on_destroy = false`
- `openspec/specs/e2e-test-fixture/spec.md` / `tests/e2e/README.md` — destroy contract clarified
- `AGENTS.md` — document decommissioning + archive-on-destroy behavior
- **BREAKING:** users who relied on `terraform destroy` / removing YAML entries to permanently delete
  repos will now get archived repos instead. To permanently delete: drop the archived repo from
  state, then delete manually via GitHub UI/API.
- The GitHub wiki (`wiki/Troubleshooting.md`, a separate `.wiki` repo) references
  `archive_on_destroy = false` as a delete workaround and is updated separately, outside this PR.
