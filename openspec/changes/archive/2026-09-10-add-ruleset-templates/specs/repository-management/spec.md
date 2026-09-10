## ADDED Requirements

### Requirement: Ruleset Templates

The system SHALL support referencing ruleset definitions as reusable templates by name, so that
common protection patterns do not have to be restated in full for every repository or group.

Templates are the same definitions as regular rulesets: both are read from `*.yml` files in
`<config_path>/ruleset/`. A definition becomes a template purely by being referenced with the
`template` key rather than by a bare name. The shipped defaults live in
`<config_path>/ruleset/default-rulesets.yml`.

A `rulesets:` entry MAY therefore take either form:

- a bare string — a direct reference to a ruleset by name
- an object with a `template` key — a template reference, where any sibling keys override the
  corresponding keys of the referenced definition

Template references are resolved for entries collected from both group and repository
configurations, and resolved templates are merged into the same ruleset map as direct references.

#### Scenario: Reference template by name

- **GIVEN** a ruleset `strict-main` is defined in `<config_path>/ruleset/default-rulesets.yml`
- **AND** a repository specifies `rulesets: [{ template: strict-main }]`
- **WHEN** Terraform is planned
- **THEN** the definition is resolved and applied to the repository
- **AND** the resolved entry is keyed as `tpl-strict-main-<index>` to avoid collisions with
  direct references

#### Scenario: Override template settings

- **GIVEN** a template `strict-main` sets `enforcement: active`
- **AND** a repository specifies `rulesets: [{ template: strict-main, enforcement: evaluate }]`
- **WHEN** Terraform is planned
- **THEN** the override value `evaluate` is used instead of the template's `active`
- **AND** the `template` key itself is excluded from the resolved ruleset

#### Scenario: Mix templates with direct references

- **GIVEN** a repository specifies both template references and direct ruleset names
- **WHEN** Terraform is planned
- **THEN** both template-based and directly referenced rulesets are applied to the repository

#### Scenario: Same template referenced more than once

- **GIVEN** a repository resolves two entries that both reference `template: strict-main`
- **WHEN** Terraform is planned
- **THEN** each resolved entry receives a distinct `tpl-strict-main-<index>` key
- **AND** neither entry silently displaces the other

#### Scenario: Template not found

- **GIVEN** a repository references `template: nonexistent`
- **AND** no definition with that name exists in `<config_path>/ruleset/`
- **WHEN** Terraform is planned
- **THEN** the `template_references` check reports the offending repository and template name
- **AND** the message lists the available template names

#### Scenario: Default templates provided

- **WHEN** the user initializes the project from the template
- **THEN** `<config_path>/ruleset/default-rulesets.yml` contains definitions usable as templates
- **AND** includes `strict-main` requiring 2 approvals, code owner review, and linear history
- **AND** includes `relaxed-devel` requiring 1 approval on `refs/heads/devel`
- **AND** includes `tag-protection` restricting deletion and update of `refs/tags/v*`

#### Scenario: Direct references exclude organization-scoped rulesets

- **GIVEN** a definition carries `scope: organization`
- **WHEN** a repository or group references it by bare name in `rulesets:`
- **THEN** the reference does not resolve to a repository ruleset
- **AND** the organization ruleset is applied only through its own `repository_name` conditions
