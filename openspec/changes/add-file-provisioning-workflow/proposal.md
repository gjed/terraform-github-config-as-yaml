# Change: Add File Provisioning Workflow via Branch Strategy

## Why

Terraform's GitHub provider creates commits that are unsigned, which conflicts with branch protection
rules requiring signed commits. Additionally, when Terraform directly pushes files, there's no review
opportunity for the provisioned content.

This change introduces a branch-based workflow where Terraform provisions files to a dedicated branch,
and an optional GitHub Action creates signed PRs for review and merge.

## What Changes

- **NEW**: File provisioning capability that writes to a configurable branch (default: `automation/provisioning`)
- **NEW**: Branch configuration option for provisioned files
- **NEW**: Optional GitHub Action workflow for creating signed PRs from provisioning branch
- **BREAKING**: None - this is additive functionality

## Impact

- Affected specs: `repository-management` (new capability for file provisioning)
- Affected code:
  - `modules/repository/` - new file provisioning logic
  - `config/` schema - new `provisioning` configuration
  - `.github/workflows/` (optional) - PR creation workflow
