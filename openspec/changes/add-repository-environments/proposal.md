## Why

The module cannot manage repository environments. Deployment branch policies, required reviewers, wait timers
and environment secrets and variables have to be set by hand in the UI or API, and they drift silently from the
YAML. This surfaced while hardening this repository itself: the `e2e` environment holds a token that can
delete repositories in the test organization and had no deployment branch policy, so any branch could run a
modified workflow against it. It was fixed through the API because the module had no way to express it.

Tracked in [#94](https://github.com/gjed/terraform-github-config-as-yaml/issues/94).

## What Changes

- Add an `environments:` map to group and repository YAML, keyed by environment name. Groups apply in order and
  a repository entry replaces a group entry of the same name, like the repository-level `secrets:` and
  `variables:` blocks.
- Each environment supports `wait_timer`, `can_admins_bypass`, `prevent_self_review`, `reviewers` (users by
  login, teams by slug), `deployment_branch_policy`, `secrets` and `variables`.
- `deployment_branch_policy` takes either `protected_branches: true` or `custom_branch_policies: true` with
  `branch_patterns` and `tag_patterns`. The two are mutually exclusive.
- Environment secrets are `env:VAR_NAME` references resolved from `secret_values`, exactly like repository
  secrets. Values never appear in YAML, outputs or error messages.
- Team reviewers resolve like ruleset `required_reviewers`: a slug from `config/team/` resolves from the managed
  team, any other slug is looked up. User reviewers are looked up by login.
- Environments of private repositories are skipped on the `free` subscription tier, with a visible
  `skipped_environments` output and a warning from `scripts/validate-config.py`.
- Validate the new block in `scripts/validate-config.py`, and enforce the mutual-exclusion rule again in a
  Terraform `precondition` so module consumers get it too.

## Capabilities

### New Capabilities

- `repository-environments`: repository environments with protection rules, deployment branch and tag
  policies, reviewers, and environment-scoped secrets and variables, defined in groups and repositories.

### Modified Capabilities

(none)

## Impact

- New resources: `github_repository_environment`, `github_repository_environment_deployment_policy`,
  `github_actions_environment_secret`, `github_actions_environment_variable`, and `github_user` and
  `github_team` data sources for reviewers.
- Affected code: `modules/repository/{main,variables,outputs}.tf`, `main.tf`, `yaml-config.tf`, `outputs.tf`,
  `scripts/validate-config.py`, `tests/`.
- Affected docs: `README.md`, `AGENTS.md`, `config/group/default-groups.yml`.
- No breaking change: `environments` is optional and defaults to none. The provider floor stays at `>= 6.12.0`.
- Environment secret values are stored in Terraform state, like repository secrets.
- Moving this repository's own `e2e` environment into the configuration repository is out of scope.
