## ADDED Requirements

### Requirement: Ruleset Templates

The system SHALL support pre-built ruleset templates that users can reference by name instead of defining
full ruleset configurations. Templates are defined in `config/ruleset/templates.yml` (requires
`add-split-config-files` for directory support) and can be used in groups or repository configurations.

#### Scenario: Reference template by name

- **GIVEN** a template `strict-main` is defined in `config/ruleset/templates.yml`
- **AND** a repository specifies `rulesets: [{ template: strict-main }]`
- **WHEN** Terraform is planned
- **THEN** the template configuration is resolved and applied to the repository

#### Scenario: Override template settings

- **GIVEN** a template `strict-main` defines `required_approving_review_count: 2`
- **AND** a repository specifies `rulesets: [{ template: strict-main, rules: { pull_request: { required_approving_review_count: 1 } } }]`
- **WHEN** Terraform is planned
- **THEN** the override value of `1` is used instead of the template's `2`

#### Scenario: Mix templates with custom rulesets

- **GIVEN** a repository specifies both template references and custom rulesets
- **WHEN** Terraform is planned
- **THEN** both template-based and custom rulesets are applied to the repository

#### Scenario: Template not found

- **GIVEN** a repository references `template: nonexistent`
- **AND** no template with that name exists
- **WHEN** Terraform is planned
- **THEN** Terraform fails with an error indicating the template was not found

#### Scenario: Default templates provided

- **WHEN** the user initializes the project from the template
- **THEN** `config/ruleset/templates.yml` contains default templates for common patterns
- **AND** includes `strict-main` for strict main branch protection
- **AND** includes `relaxed-dev` for development branch protection
- **AND** includes `release-tags` for tag protection
