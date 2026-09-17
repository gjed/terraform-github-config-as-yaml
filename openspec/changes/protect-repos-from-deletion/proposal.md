## Why

The `github_repository` resource deletes repositories when they are removed from configuration or state. Deleting a GitHub repository is catastrophic and irreversible. This is especially dangerous with repository partitioning (#36), where switching partitions causes repos to drop out of Terraform's view, triggering destroy plans.

`prevent_destroy` cannot solve this: Terraform requires it to be a literal boolean (no variables/expressions), and setting it `true` deadlocks the module's normal `for_each`-based repo removal and partition narrowing — every orphaned instance trips a permanent plan error. It was already dropped from the module in the fix-partition-narrowing-destroy change.

## What Changes

- **BREAKING:** Hardcode `archive_on_destroy = true` on the `github_repository` resource in `modules/repository/main.tf`. On any destroy, the GitHub provider archives the repository (via the edit API, `archived: true`) instead of permanently deleting it. Previously repos were deleted on destroy (`archive_on_destroy` defaulted to `false`).
- No variable, no YAML config, no per-repo/group override, no validation warning. The value is a fixed module contract.
- `prevent_destroy` is intentionally not set.
- Document the safe repository decommissioning process and the archive-on-destroy behavior.

## Capabilities

### New Capabilities

- `deletion-protection`: Repositories are archived instead of deleted on destroy via a hardcoded `archive_on_destroy = true`. Covers the Terraform resource lifecycle and the documented decommissioning process.

### Modified Capabilities

- `repository-management`: `archive_on_destroy = true` is a fixed module contract on the repository resource.

## Impact

- `modules/repository/main.tf` — hardcoded `archive_on_destroy = true`, `prevent_destroy` line removed
- `AGENTS.md` / README — document decommissioning + archive-on-destroy behavior
- **BREAKING:** users who relied on `terraform destroy` / removing YAML entries to permanently delete repos will now get archived repos instead. To permanently delete: archive is removed from state, then delete manually via GitHub UI/API.
