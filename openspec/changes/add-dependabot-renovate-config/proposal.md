# Change: Add Dependabot and Renovate Configuration Management

## Why

Dependency update configuration (Dependabot/Renovate) must be manually created in each repository.
This leads to:

- Inconsistent update schedules across repositories
- Missing configs in new repositories
- No centralized policy for dependency updates
- Difficult to switch between Dependabot and Renovate

## What Changes

- **NEW**: Dependabot configuration management via YAML
- **NEW**: Renovate configuration management via YAML
- **NEW**: Configuration groups for shared dependency update policies
- **NEW**: Support for using both tools (different repos)
- Uses file provisioning workflow for delivery (see `add-file-provisioning-workflow`)

## Impact

- Affected specs: `repository-management` (new dependency update configuration)
- Affected code:
  - `config/` schema - new `dependabot` and `renovate` configuration blocks
  - `modules/repository/` - file generation logic
  - `templates/` - configuration file templates

## Dependencies

This change depends on:

- `add-file-provisioning-workflow` - Provides the branch-based file provisioning mechanism

## References

- GitHub Issue: #6
