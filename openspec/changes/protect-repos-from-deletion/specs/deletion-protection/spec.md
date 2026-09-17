## ADDED Requirements

### Requirement: Archive-on-Destroy

The repository submodule SHALL set `archive_on_destroy = true` on the `github_repository` resource as a hardcoded, non-configurable value. On destroy, the GitHub provider SHALL archive the repository instead of permanently deleting it.

#### Scenario: Repository removed from configuration

- **GIVEN** a repository managed by the module
- **WHEN** the repository is removed from configuration (or drops out of a partition) and `terraform apply` runs
- **THEN** the GitHub provider archives the repository via the edit API (`archived: true`)
- **AND** the repository is not permanently deleted
- **AND** the resource is removed from Terraform state

#### Scenario: Repository already archived

- **GIVEN** a managed repository that is already archived
- **WHEN** it is destroyed
- **THEN** the provider performs no destructive API call
- **AND** the resource is removed from Terraform state

#### Scenario: Value is not configurable

- **WHEN** a user inspects the module
- **THEN** `archive_on_destroy` is a fixed `true` with no variable, YAML key, or per-repo/group override

______________________________________________________________________

### Requirement: Decommissioning Documentation

The module documentation SHALL describe the safe process for removing a repository from Terraform management, including that repositories are archived rather than deleted on destroy.

#### Scenario: Documentation covers decommissioning

- **WHEN** a user reads the module documentation (AGENTS.md)
- **THEN** they find a section explaining:
  - The normal YAML-entry removal process for repositories
  - That removal archives the repository instead of deleting it
  - How to permanently delete a repository if truly intended (remove from state after archiving, then delete via GitHub UI/API)
