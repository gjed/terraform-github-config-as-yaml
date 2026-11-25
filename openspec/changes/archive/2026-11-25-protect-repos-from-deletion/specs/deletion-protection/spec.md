## ADDED Requirements

### Requirement: Archive-on-Destroy

The repository module SHALL expose an `archive_on_destroy` variable defaulting to `true` and pass it
to the `github_repository` resource. When `true`, the GitHub provider SHALL archive the repository on
destroy instead of permanently deleting it.

#### Scenario: Repository removed from configuration

- **GIVEN** a repository managed by the module with the default `archive_on_destroy = true`
- **WHEN** the repository is removed from configuration and `terraform apply` runs
- **THEN** the GitHub provider archives the repository via the edit API (`archived: true`)
- **AND** the repository is not permanently deleted
- **AND** the resource is removed from Terraform state

#### Scenario: Repository already archived

- **GIVEN** a managed repository that is already archived
- **WHEN** it is destroyed with `archive_on_destroy = true`
- **THEN** the provider performs no destructive API call
- **AND** the resource is removed from Terraform state

#### Scenario: Hard delete when opted out

- **GIVEN** a consumer (e.g. the e2e test fixture) sets `archive_on_destroy = false`
- **WHEN** a repository is destroyed
- **THEN** the GitHub provider permanently deletes the repository
- **AND** the resource is removed from Terraform state

#### Scenario: Default is archive

- **WHEN** `archive_on_destroy` is not specified
- **THEN** the value defaults to `true` and repositories are archived on destroy

______________________________________________________________________

### Requirement: Decommissioning Documentation

The module documentation SHALL describe the safe process for removing a repository from Terraform
management, including that repositories are archived rather than deleted on destroy.

#### Scenario: Documentation covers decommissioning

- **WHEN** a user reads the module documentation (AGENTS.md)
- **THEN** they find a section explaining:
  - The normal YAML-entry removal process for repositories
  - That removal archives the repository instead of deleting it
  - How to permanently delete a repository if truly intended (drop from state via
    `offboard-repos.sh` or `terraform state rm`, then delete via GitHub UI/API)
