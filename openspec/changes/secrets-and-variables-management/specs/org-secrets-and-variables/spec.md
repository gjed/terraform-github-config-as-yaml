## ADDED Requirements

### Requirement: Organization-level Actions secrets

The module SHALL support defining GitHub Actions organization secrets via YAML files in
`config/secret/`. Each secret is defined under the `actions_secrets` key with a name, a
`value` using the `env:VAR_NAME` pattern, and a `visibility` setting (`all`, `private`,
or `selected`). When `visibility` is `selected`, a `selected_repositories` list of
repository names MUST be provided. The secret value SHALL be resolved from the
`secret_values` Terraform input variable at plan time. The module SHALL create a
`github_actions_organization_secret` resource for each defined secret.

#### Scenario: Create an org-level Actions secret with visibility "all"

- **WHEN** a YAML file in `config/secret/` contains an `actions_secrets` entry with
  `visibility: all` and `value: "env:MY_TOKEN"`
- **THEN** the module creates a `github_actions_organization_secret` with the secret name,
  the resolved value from `secret_values["MY_TOKEN"]`, and `visibility = "all"`

#### Scenario: Create an org-level Actions secret with visibility "selected"

- **WHEN** a YAML file in `config/secret/` contains an `actions_secrets` entry with
  `visibility: selected` and `selected_repositories: [repo-a, repo-b]`
- **THEN** the module creates a `github_actions_organization_secret` with
  `visibility = "selected_repositories"` and resolves the repository names to IDs from
  the managed repository set

#### Scenario: Missing env reference in secret_values

- **WHEN** a secret references `env:UNDEFINED_VAR` and `secret_values` does not contain
  the key `UNDEFINED_VAR`
- **THEN** the module SHALL surface a validation error at plan time

#### Scenario: Org secrets on personal account

- **WHEN** `is_organization` is `false` in `config/config.yml`
- **THEN** all organization-level secret/variable resources SHALL be skipped (no error)

### Requirement: Organization-level Actions variables

The module SHALL support defining GitHub Actions organization variables via YAML files in
`config/secret/`. Each variable is defined under the `actions_variables` key with a name,
a plaintext `value`, and a `visibility` setting. When `visibility` is `selected`, a
`selected_repositories` list MUST be provided. The module SHALL create a
`github_actions_organization_variable` resource for each defined variable.

#### Scenario: Create an org-level Actions variable with visibility "private"

- **WHEN** a YAML file in `config/secret/` contains an `actions_variables` entry with
  `value: "production"` and `visibility: private`
- **THEN** the module creates a `github_actions_organization_variable` with the variable
  name, value `"production"`, and `visibility = "private"`

#### Scenario: Variable value stored in plaintext

- **WHEN** an `actions_variables` entry has `value: "staging"`
- **THEN** the value is used directly without `env:` resolution (variables are non-sensitive)

#### Scenario: Variable with selected repositories

- **WHEN** an `actions_variables` entry has `visibility: selected` and
  `selected_repositories: [my-app]`
- **THEN** the module creates the variable with `visibility = "selected"` and resolves
  `my-app` to its repository ID

### Requirement: Organization-level Dependabot secrets

The module SHALL support defining Dependabot organization secrets via YAML files in
`config/secret/`. Each secret is defined under the `dependabot_secrets` key with a name,
a `value` using the `env:VAR_NAME` pattern, and a `visibility` setting. The module SHALL
create a `github_dependabot_organization_secret` resource for each defined secret.

#### Scenario: Create an org-level Dependabot secret

- **WHEN** a YAML file in `config/secret/` contains a `dependabot_secrets` entry with
  `value: "env:REGISTRY_PASSWORD"` and `visibility: private`
- **THEN** the module creates a `github_dependabot_organization_secret` with the resolved
  value and `visibility = "private"`

#### Scenario: Dependabot secret with selected repositories

- **WHEN** a `dependabot_secrets` entry has `visibility: selected` and
  `selected_repositories: [my-api]`
- **THEN** the module creates the secret with `visibility = "selected"` and resolves
  `my-api` to its repository ID

### Requirement: Config loading from config/secret/ directory

The module SHALL load all `*.yml` files from `config/secret/` in alphabetical order,
merging entries across files. Duplicate keys across files SHALL be detected and reported
as warnings (consistent with other config types). The directory SHALL be optional —
when absent or empty, no org-level secrets/variables are created.

#### Scenario: Multiple files in config/secret/

- **WHEN** `config/secret/` contains `team-a.yml` and `team-b.yml`, both defining
  `actions_secrets`
- **THEN** secrets from both files are merged; duplicate secret names across files are
  detected and warned

#### Scenario: Missing config/secret/ directory

- **WHEN** `config/secret/` does not exist
- **THEN** no org-level secrets or variables are created (no error)

### Requirement: New secret_values input variable

The module SHALL accept a `secret_values` input variable of type `map(string)` marked
as `sensitive`. This variable provides the actual values for secrets referenced via
`env:VAR_NAME` in YAML configurations. It SHALL be used for both org-level and
repo-level secret resolution.

#### Scenario: Passing secret values via Terraform variable

- **WHEN** the consumer sets `secret_values = { DEPLOY_TOKEN = "ghp_abc123" }`
- **THEN** any YAML secret with `value: "env:DEPLOY_TOKEN"` resolves to `"ghp_abc123"`

#### Scenario: Empty secret_values with no secrets configured

- **WHEN** `secret_values` is not provided (defaults to `{}`) and no secrets are
  defined in YAML
- **THEN** the module operates normally with no secret resources created

### Requirement: Selected repositories reference validation

The module SHALL validate that all repository names in `selected_repositories` lists
correspond to repositories defined in the module's configuration. Invalid references
SHALL be surfaced as validation errors at plan time.

#### Scenario: Valid selected repository reference

- **WHEN** `selected_repositories` contains `my-app` and `my-app` is defined in
  `config/repository/`
- **THEN** the reference is resolved to the repository's ID without error

#### Scenario: Invalid selected repository reference

- **WHEN** `selected_repositories` contains `nonexistent-repo` which is not defined
  in `config/repository/`
- **THEN** a validation error is raised at plan time indicating the invalid reference
