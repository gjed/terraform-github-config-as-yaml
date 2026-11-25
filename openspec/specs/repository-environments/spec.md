# repository-environments Specification

## Purpose

Define the requirements for managing GitHub repository environments via YAML configuration: protection
rules, reviewers, deployment branch and tag policies, environment secrets and variables, and subscription
tier gating.

## Requirements

### Requirement: Repository environments

The system SHALL support an `environments` map in group and repository YAML configs, keyed by environment name.
Each entry SHALL create a `github_repository_environment` on every repository that inherits it. The supported
keys are `wait_timer` (minutes, 0-43200, default 0), `can_admins_bypass` (default `true`),
`prevent_self_review` (default `false`), `reviewers`, `deployment_branch_policy`, `secrets` and `variables`.
Any other key inside an environment SHALL be reported by `scripts/validate-config.py` as an error.

Groups SHALL apply in order and a repository entry SHALL replace a group entry with the same environment name
as a whole; the properties of the two definitions are not merged. `environments` is optional and defaults to
no environments.

#### Scenario: Environment defined in a repository

- **WHEN** a repository config contains `environments.production` with `wait_timer: 10`
- **THEN** the module creates a `github_repository_environment` named `production` on that repository with a
  10 minute wait timer, admins allowed to bypass, and self-review allowed

#### Scenario: Environment inherited from a group

- **WHEN** a group defines `environments.staging` and a repository lists that group
- **THEN** the repository gets a `staging` environment

#### Scenario: Group order and repository override

- **WHEN** two groups define `environments.production` with different `wait_timer` values and the repository
  lists both groups
- **THEN** the later group's definition is used
- **AND** when the repository also defines `environments.production`, the repository's definition replaces the
  group definition entirely, including its secrets and variables

#### Scenario: Distinct environments are kept

- **WHEN** a group defines `staging` and the repository defines `production`
- **THEN** the repository gets both environments

#### Scenario: Wait timer out of range

- **WHEN** an environment sets `wait_timer` below 0 or above 43200
- **THEN** `scripts/validate-config.py` reports an error
- **AND** `terraform plan` fails on a `precondition` of the environment resource

#### Scenario: Unknown environment key

- **WHEN** an environment contains a key outside the supported set, such as `wait_time`
- **THEN** `scripts/validate-config.py` reports an error naming the environment and the key

### Requirement: Environment reviewers

An environment MAY define `reviewers.users` (GitHub logins) and `reviewers.teams` (team slugs). At most 6
reviewers in total are allowed, the limit GitHub enforces. When both lists are empty or absent, no reviewers
block is created.

A team slug SHALL resolve exactly like a ruleset `required_reviewers` slug: a slug of a team defined in
`config/team/` resolves from that managed team, so the team and the environment can be created in the same
apply, and any other slug is resolved with a `github_team` lookup that fails the plan when the team does not
exist. A user login SHALL be resolved with a `github_user` lookup that fails the plan when the user does not
exist. Lookups are made only for environments that are applied, never for skipped ones. GitHub rejects reviewers that
cannot access the repository, so the environment SHALL be created after the repository's team and collaborator
access grants, and a reviewer SHALL be granted access to the repository through `teams:` or `collaborators:`.

#### Scenario: Managed team reviewer

- **GIVEN** `config/team/` defines team `security-team`
- **WHEN** an environment sets `reviewers.teams: [security-team]`
- **THEN** the environment requires approval from the managed team, and is created after the team

#### Scenario: External team and user reviewers

- **WHEN** an environment sets `reviewers.teams: [platform]` and `reviewers.users: [octocat]` and `platform` is
  not defined in `config/team/`
- **THEN** both are resolved to IDs through lookups before the environment is created

#### Scenario: Too many reviewers

- **WHEN** an environment lists more than 6 reviewers in total
- **THEN** `scripts/validate-config.py` reports an error

### Requirement: Deployment branch policy

An environment MAY define `deployment_branch_policy` with `protected_branches`, `custom_branch_policies`,
`branch_patterns` and `tag_patterns`. `protected_branches: true` limits deployments to branches with branch
protection. `custom_branch_policies: true` limits deployments to the listed patterns, and the module SHALL
create one `github_repository_environment_deployment_policy` per entry of `branch_patterns` (as
`branch_pattern`) and of `tag_patterns` (as `tag_pattern`). When neither flag is true, no deployment branch
policy block is created and any branch may deploy.

`protected_branches` and `custom_branch_policies` SHALL be mutually exclusive, `branch_patterns` and
`tag_patterns` SHALL be accepted only together with `custom_branch_policies: true`, and
`custom_branch_policies: true` SHALL list at least one pattern, because an empty list would let no branch or tag
deploy. All three rules SHALL be enforced
by `scripts/validate-config.py` and by a `precondition` on the environment resource, so consumers using the
module directly are protected as well.

#### Scenario: Protected branches only

- **WHEN** an environment sets `deployment_branch_policy.protected_branches: true`
- **THEN** only branches with branch protection can deploy to the environment
- **AND** no deployment policy resources are created

#### Scenario: Custom branch and tag patterns

- **WHEN** an environment sets `custom_branch_policies: true`, `branch_patterns: [main, "release/*"]` and
  `tag_patterns: ["v*"]`
- **THEN** the module creates three deployment policies for that environment: two branch patterns and one tag
  pattern

#### Scenario: Mutually exclusive flags

- **WHEN** an environment sets both `protected_branches: true` and `custom_branch_policies: true`
- **THEN** `scripts/validate-config.py` reports an error
- **AND** `terraform plan` fails on a `precondition` of the environment resource

#### Scenario: Custom policies without patterns

- **WHEN** an environment sets `custom_branch_policies: true` with no `branch_patterns` and no `tag_patterns`
- **THEN** `scripts/validate-config.py` reports an error
- **AND** `terraform plan` fails on a `precondition` of the environment resource

#### Scenario: Patterns without custom policies

- **WHEN** an environment lists `branch_patterns` or `tag_patterns` without `custom_branch_policies: true`
- **THEN** `scripts/validate-config.py` reports an error
- **AND** `terraform plan` fails on a `precondition` of the environment resource

### Requirement: Environment secrets and variables

An environment MAY define `secrets` and `variables`, each a map of name to definition with a `value`. A secret
`value` SHALL be an `env:VAR_NAME` reference resolved from the `secret_values` input variable, and the module
SHALL create a `github_actions_environment_secret` for it. A variable `value` is plaintext and is converted to a
string, and the module SHALL create a `github_actions_environment_variable` for it. Names SHALL match
`^[A-Z_][A-Z0-9_]*$` and SHALL NOT start with `GITHUB_`.

A secret whose reference is missing from `secret_values`, or whose value is not an `env:` reference, SHALL fail
`terraform plan`. Error messages SHALL name the secret and the reference and SHALL NOT contain the value.
`scripts/validate-config.py` SHALL reject invalid names and secret values that are not `env:VAR_NAME`
references, without echoing the value.

#### Scenario: Environment secret resolved from secret_values

- **WHEN** an environment defines secret `E2E_GITHUB_TOKEN` with `value: "env:E2E_GITHUB_TOKEN"` and
  `secret_values` contains `E2E_GITHUB_TOKEN`
- **THEN** a `github_actions_environment_secret` is created in that environment with the resolved value

#### Scenario: Unresolvable secret reference

- **WHEN** an environment secret references `env:MISSING` and `secret_values` has no `MISSING` key
- **THEN** `terraform plan` fails with an error naming the secret and the reference
- **AND** the error contains no secret value

#### Scenario: Literal secret value

- **WHEN** an environment secret has a literal `value` that is not an `env:VAR_NAME` reference
- **THEN** `scripts/validate-config.py` reports an error that does not echo the value

#### Scenario: Environment variable

- **WHEN** an environment defines variable `LOG_LEVEL` with `value: debug`
- **THEN** a `github_actions_environment_variable` is created in that environment with value `debug`

#### Scenario: Invalid name

- **WHEN** an environment secret or variable is named `lowercase` or `GITHUB_TOKEN`
- **THEN** `scripts/validate-config.py` reports an error
- **AND** `terraform plan` fails on a `precondition`

### Requirement: Environment outputs expose names only

The module SHALL expose the names of managed environments, environment secrets and environment variables, and
SHALL NOT expose secret or variable values. The root `repository_environments` output SHALL list, per
repository, the environment names with their secret names and variable names.

#### Scenario: Output lists names

- **WHEN** a repository has environment `production` with secret `DEPLOY_TOKEN`
- **THEN** the `repository_environments` output lists `production` and `DEPLOY_TOKEN` for that repository
- **AND** no secret value appears in any output

### Requirement: Environment subscription tier gating

On the `free` subscription tier, environments of repositories whose effective visibility is not `public` SHALL
be skipped by Terraform, because GitHub offers environments, required reviewers, wait timers and deployment
branch policies on private repositories only on paid plans. The whole environment is skipped, including its
secrets, variables and deployment policies. On `pro`, `team` and `enterprise`, and for public repositories on
any tier, no environment is skipped.

Skipped environments SHALL be reported by the root `skipped_environments` output, which lists the affected
repositories with their environment names and the tier, and is `null` when nothing is skipped.
`scripts/validate-config.py` SHALL emit a warning for each such repository, using the effective visibility
after group inheritance.

#### Scenario: Private repository on the free tier

- **GIVEN** `subscription: free` and a private repository with `environments.production`
- **WHEN** `terraform plan` is executed
- **THEN** no environment resources are planned for that repository
- **AND** the `skipped_environments` output lists the repository and `production`
- **AND** `scripts/validate-config.py` prints a warning for the repository

#### Scenario: Public repository on the free tier

- **GIVEN** `subscription: free` and a public repository with `environments.production`
- **THEN** the environment is created and `skipped_environments` is `null`

#### Scenario: Private repository on a paid tier

- **GIVEN** `subscription: team` and a private repository with `environments.production`
- **THEN** the environment is created and `skipped_environments` is `null`
