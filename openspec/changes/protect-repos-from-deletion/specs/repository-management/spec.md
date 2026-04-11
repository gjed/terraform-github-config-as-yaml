## MODIFIED Requirements

### Requirement: Repository Resource Management

The system SHALL create and manage GitHub repositories using the Terraform GitHub provider.
Repositories SHALL have `prevent_destroy = true` in their lifecycle block and `archive_on_destroy`
set according to the global configuration default.

#### Scenario: Create new repository

- **WHEN** a repository is defined in configuration that does not exist in GitHub
- **AND** `terraform apply` is executed
- **THEN** the repository is created with the specified settings
- **AND** `archive_on_destroy` is set according to the global default

#### Scenario: Update existing repository

- **WHEN** a repository setting is changed in configuration
- **AND** `terraform apply` is executed
- **THEN** the repository is updated to match the new configuration

#### Scenario: Repository settings applied

- **WHEN** a repository is created or updated
- **THEN** the following settings are applied: visibility, description, homepage_url, has_wiki,
  has_issues, has_projects, has_discussions, allow_merge_commit, allow_squash_merge,
  allow_rebase_merge, allow_auto_merge, allow_update_branch, delete_branch_on_merge,
  web_commit_signoff_required, vulnerability_alerts, topics, license_template, archive_on_destroy

#### Scenario: Destroy repository blocked

- **WHEN** a repository is removed from configuration
- **AND** `terraform plan` is executed
- **THEN** Terraform refuses to plan the destruction due to `prevent_destroy = true`
