## ADDED Requirements

### Requirement: Repository-level Actions secrets

The module SHALL support defining GitHub Actions secrets at the repository level via
`secrets.actions` in group and/or repository YAML configs. Each secret has a name and a
`value` using the `env:VAR_NAME` pattern. The value SHALL be resolved from the
`secret_values` Terraform input variable. The module SHALL create a `github_actions_secret`
resource for each defined secret per repository.

#### Scenario: Define Actions secret in repository config

- **WHEN** a repository YAML config contains `secrets.actions.DATABASE_URL` with
  `value: "env:MY_REPO_DATABASE_URL"`
- **THEN** the module creates a `github_actions_secret` for that repository with the
  resolved value from `secret_values["MY_REPO_DATABASE_URL"]`

#### Scenario: Missing env reference for repo-level secret

- **WHEN** a repo secret references `env:MISSING_KEY` and `secret_values` does not
  contain `MISSING_KEY`
- **THEN** the module SHALL surface a validation error at plan time

### Requirement: Repository-level Actions variables

The module SHALL support defining GitHub Actions variables at the repository level via
`variables.actions` in group and/or repository YAML configs. Each variable has a name
and a plaintext `value`. The module SHALL create a `github_actions_variable` resource
for each defined variable per repository.

#### Scenario: Define Actions variable in repository config

- **WHEN** a repository YAML config contains `variables.actions.DEPLOY_ENV` with
  `value: "production"`
- **THEN** the module creates a `github_actions_variable` for that repository with
  `variable_name = "DEPLOY_ENV"` and `value = "production"`

#### Scenario: Variable value is plaintext

- **WHEN** a `variables.actions` entry has `value: "staging"`
- **THEN** the value is used directly without `env:` resolution

### Requirement: Repository-level Dependabot secrets

The module SHALL support defining Dependabot secrets at the repository level via
`secrets.dependabot` in group and/or repository YAML configs. Each secret has a name
and a `value` using the `env:VAR_NAME` pattern. The module SHALL create a
`github_dependabot_secret` resource for each defined secret per repository.

#### Scenario: Define Dependabot secret in repository config

- **WHEN** a repository YAML config contains `secrets.dependabot.REGISTRY_PASSWORD`
  with `value: "env:REGISTRY_PASSWORD"`
- **THEN** the module creates a `github_dependabot_secret` for that repository with
  the resolved value

### Requirement: Group inheritance for secrets and variables

Secrets and variables defined in groups SHALL be inherited by repositories assigned to
those groups. When a repository is assigned multiple groups, secrets/variables are merged
in group order — later groups override earlier groups by secret/variable name.
Repository-level definitions SHALL override group-level definitions by name.

The override is full replacement — if a repo overrides a secret name, the entire
definition is replaced (no partial merge of individual properties).

#### Scenario: Repo inherits secrets from group

- **WHEN** group `internal` defines `secrets.actions.INTERNAL_TOKEN` and repository
  `my-repo` is assigned group `["internal"]` with no repo-level secret overrides
- **THEN** `my-repo` inherits `INTERNAL_TOKEN` as an Actions secret

#### Scenario: Repo overrides group secret

- **WHEN** group `internal` defines `secrets.actions.API_KEY` with
  `value: "env:GROUP_API_KEY"` and repository `my-repo` defines
  `secrets.actions.API_KEY` with `value: "env:REPO_API_KEY"`
- **THEN** `my-repo` uses `env:REPO_API_KEY` (repo overrides group)

#### Scenario: Multiple groups merge secrets

- **WHEN** repository `my-repo` is assigned groups `["base", "internal"]`, group `base`
  defines `secrets.actions.TOKEN_A`, and group `internal` defines `secrets.actions.TOKEN_B`
- **THEN** `my-repo` inherits both `TOKEN_A` and `TOKEN_B`

#### Scenario: Later group overrides earlier group

- **WHEN** repository `my-repo` is assigned groups `["base", "internal"]`, both groups
  define `secrets.actions.SHARED_TOKEN` with different values
- **THEN** `my-repo` uses the definition from `internal` (later group wins)

#### Scenario: Repo overrides group variable

- **WHEN** group `internal` defines `variables.actions.DEPLOY_ENV` with `value: "staging"`
  and repository `my-repo` defines `variables.actions.DEPLOY_ENV` with
  `value: "production"`
- **THEN** `my-repo` uses `value: "production"` (repo overrides group)

### Requirement: Repo-level secrets work for all account types

Repository-level secrets and variables SHALL work for both organization accounts and
personal accounts. There is no subscription tier restriction on repository-level
secrets/variables.

#### Scenario: Personal account with repo secrets

- **WHEN** `is_organization` is `false` and a repository defines `secrets.actions.MY_SECRET`
- **THEN** the module creates a `github_actions_secret` for that repository (no skip)

#### Scenario: Free-tier org with repo secrets

- **WHEN** `subscription` is `free` and a repository defines `secrets.actions.MY_SECRET`
- **THEN** the module creates the secret without restriction (secrets are not tier-gated)
