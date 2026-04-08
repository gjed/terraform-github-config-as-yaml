## ADDED Requirements

### Requirement: File Provisioning via Branch Strategy

The system SHALL support provisioning files to repositories via a dedicated branch, enabling signed
commit workflows through PR-based merging.

#### Scenario: Provision file to automation branch

- **GIVEN** a repository defines files to provision (e.g., `dependabot.yml`, `LICENSE`)
- **AND** `provisioning.branch` is set to `automation/provisioning`
- **WHEN** `terraform apply` is executed
- **THEN** the files are created/updated on the `automation/provisioning` branch
- **AND** the main/default branch is not directly modified

#### Scenario: Default provisioning branch

- **GIVEN** a repository defines files to provision
- **AND** no explicit `provisioning.branch` is configured
- **WHEN** `terraform apply` is executed
- **THEN** the files are provisioned to the default branch `automation/provisioning`

#### Scenario: Custom provisioning branch per repository

- **GIVEN** a repository defines `provisioning: { branch: "terraform/files" }`
- **WHEN** files are provisioned
- **THEN** the files are created on the `terraform/files` branch

#### Scenario: Branch creation on first provision

- **GIVEN** a repository does not have the provisioning branch
- **WHEN** files are provisioned for the first time
- **THEN** the provisioning branch is created from the default branch
- **AND** the provisioned files are committed to it

______________________________________________________________________

### Requirement: Provisioning Branch Configuration

The system SHALL support organization-wide and repository-specific provisioning branch configuration.

#### Scenario: Organization-wide default

- **GIVEN** `config.yml` defines `provisioning: { branch: "automation/managed" }`
- **AND** a repository does not override this setting
- **WHEN** files are provisioned
- **THEN** the files are placed on the `automation/managed` branch

#### Scenario: Repository override

- **GIVEN** `config.yml` defines `provisioning: { branch: "automation/managed" }`
- **AND** a repository defines `provisioning: { branch: "custom/branch" }`
- **WHEN** files are provisioned for that repository
- **THEN** the files are placed on the `custom/branch` branch

#### Scenario: Disable provisioning for repository

- **GIVEN** a repository defines `provisioning: { enabled: false }`
- **WHEN** `terraform apply` is executed
- **THEN** no files are provisioned to that repository
- **AND** existing provisioned files are not removed

______________________________________________________________________

### Requirement: Provisioned File Management

The system SHALL track and manage provisioned files separately from repository configuration.

#### Scenario: File content from configuration

- **GIVEN** a file is defined with inline content in YAML
- **WHEN** `terraform apply` is executed
- **THEN** the file is created with the specified content on the provisioning branch

#### Scenario: File content from template

- **GIVEN** a file is defined with `template: "templates/LICENSE.mit.tpl"`
- **AND** the template uses variables like `{{ .year }}` and `{{ .owner }}`
- **WHEN** `terraform apply` is executed
- **THEN** the file is rendered with the provided variables
- **AND** created on the provisioning branch

#### Scenario: Update existing provisioned file

- **GIVEN** a provisioned file exists on the provisioning branch
- **AND** the configuration content changes
- **WHEN** `terraform apply` is executed
- **THEN** the file is updated on the provisioning branch
- **AND** a new commit is created with the changes

#### Scenario: No changes to provisioned file

- **GIVEN** a provisioned file exists on the provisioning branch
- **AND** the configuration content has not changed
- **WHEN** `terraform apply` is executed
- **THEN** no new commit is created

______________________________________________________________________

### Requirement: Provisioning PR Workflow (Optional)

The system SHALL support an optional GitHub Action workflow that creates signed PRs from the
provisioning branch.

#### Scenario: Workflow detects changes

- **GIVEN** the optional PR workflow is installed
- **AND** Terraform pushes changes to the provisioning branch
- **WHEN** the workflow is triggered
- **THEN** a PR is created from the provisioning branch to the default branch
- **AND** the PR commits are signed by the GitHub Actions bot

#### Scenario: PR already exists

- **GIVEN** a PR from the provisioning branch already exists
- **WHEN** new changes are pushed to the provisioning branch
- **THEN** the existing PR is updated (no duplicate PR created)

#### Scenario: Auto-labeling provisioned PRs

- **GIVEN** the workflow creates a PR
- **WHEN** the PR is created
- **THEN** the PR is labeled with `automated` and `terraform-managed`

#### Scenario: Workflow not installed

- **GIVEN** the repository does not have the PR workflow
- **WHEN** Terraform provisions files to the branch
- **THEN** the files remain on the provisioning branch
- **AND** manual PR creation is required to merge changes

______________________________________________________________________

### Requirement: Provisioning Commit Messages

The system SHALL use descriptive commit messages for provisioned file changes.

#### Scenario: Single file provisioned

- **GIVEN** a single file (e.g., `LICENSE`) is provisioned
- **WHEN** the commit is created
- **THEN** the commit message indicates the file: `chore: provision LICENSE`

#### Scenario: Multiple files provisioned

- **GIVEN** multiple files are provisioned in one apply
- **WHEN** the commit is created
- **THEN** the commit message summarizes the changes: `chore: provision 3 files`
- **AND** the commit body lists the affected files

#### Scenario: Custom commit message prefix

- **GIVEN** `provisioning.commit_prefix` is set to `automation:`
- **WHEN** files are provisioned
- **THEN** the commit message uses the custom prefix: `automation: provision LICENSE`
