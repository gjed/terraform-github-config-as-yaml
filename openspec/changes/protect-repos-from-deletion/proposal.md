## Why

The `github_repository` resource has `prevent_destroy = false`, meaning Terraform will happily delete
repositories when they are removed from configuration or state. Deleting a GitHub repository is
catastrophic and irreversible. This is especially dangerous with repository partitioning (#36), where
switching partitions causes repos to drop out of Terraform's view, triggering destroy plans.

## What Changes

- **BREAKING**: Set `prevent_destroy = true` on `github_repository.this` in the repository submodule.
  Terraform will refuse to destroy repositories and error out instead. Users who need to decommission a
  repo must `terraform state rm` the resource first, then manually delete via GitHub UI/API.
- Add `archive_on_destroy` as a global default setting in `config/config.yml`, defaulting to `true`.
  This is a secondary safety net: if a repository is somehow removed from Terraform state without the
  `prevent_destroy` guard (e.g., via `terraform state rm`), the GitHub provider archives the repo
  instead of deleting it.
- Document the safe repository decommissioning process.
- Add validation warning when `archive_on_destroy` is explicitly set to `false`.

## Capabilities

### New Capabilities

- `deletion-protection`: Lifecycle protection for repositories via `prevent_destroy = true` and
  configurable `archive_on_destroy` safety net. Covers the Terraform resource lifecycle, YAML
  configuration for `archive_on_destroy`, and the documented decommissioning process.

### Modified Capabilities

- `repository-management`: Add `archive_on_destroy` to the set of managed repository settings and
  document the `prevent_destroy` lifecycle behavior as a module contract.

## Impact

- `modules/repository/main.tf` — lifecycle block change, new `archive_on_destroy` argument
- `modules/repository/variables.tf` — new variable
- `yaml-config.tf` — read `archive_on_destroy` from defaults
- `main.tf` — pass `archive_on_destroy` to repository module
- `config/config.yml` — new default setting
- `scripts/validate-config.py` — new validation warning
- `AGENTS.md` / README — documentation updates
- Existing users who rely on `terraform destroy` for repo removal will need to change their workflow
