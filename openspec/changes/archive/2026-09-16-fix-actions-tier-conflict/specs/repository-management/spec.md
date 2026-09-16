## ADDED Requirements

### Requirement: Organization/Repository Actions Tier Conflict Detection

The system SHALL detect, before `terraform apply`, any repository whose resolved Actions
configuration conflicts with an organization-level `allowed_actions: selected` policy, and SHALL
report it as a validation error.

GitHub unconditionally rejects a repository-level `actions/permissions/selected-actions` request
with `409 Conflict` once the organization itself uses `allowed_actions: selected` — verified
against the live API — regardless of whether the repository's requested configuration matches the
organization's. Only omitting a repository-level `actions:` block avoids the conflict, in which
case the repository inherits the organization's allowed list automatically.

#### Scenario: Repository-level actions block conflicts with org-level selected policy

- **GIVEN** `config.yml` defines `actions.allowed_actions: selected`
- **AND** a repository (directly or via a group) defines its own `actions:` block
- **WHEN** `scripts/validate-config.py` runs
- **THEN** an error reports that the repository's `actions:` block will be rejected by GitHub
  with a 409 once the organization uses `selected`
- **AND** the error instructs removing the repository/group-level `actions:` block

#### Scenario: No conflict when organization does not use selected

- **GIVEN** `config.yml` defines `actions.allowed_actions: all` (or no `actions` block)
- **AND** a repository defines its own `actions:` block
- **WHEN** `scripts/validate-config.py` runs
- **THEN** no error is reported for that repository

#### Scenario: No conflict when repository has no actions block

- **GIVEN** `config.yml` defines `actions.allowed_actions: selected`
- **AND** a repository defines no `actions:` block, directly or via any of its groups
- **WHEN** `scripts/validate-config.py` runs
- **THEN** no error is reported for that repository
- **AND** the repository inherits the organization's allowed-actions list automatically
