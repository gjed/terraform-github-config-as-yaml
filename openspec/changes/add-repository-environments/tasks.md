## 1. Module resources

- [ ] 1.1 Add the `environments` variable and `user_ids` to `modules/repository/variables.tf`
- [ ] 1.2 Add `github_repository_environment` with `precondition`s (mutual exclusion, patterns without custom
  policies, wait timer range) to `modules/repository/main.tf`
- [ ] 1.3 Add `github_repository_environment_deployment_policy`, `github_actions_environment_secret` and
  `github_actions_environment_variable` with name and resolvability `precondition`s
- [ ] 1.4 Expose environment, secret and variable names (never values) in `modules/repository/outputs.tf`

## 2. YAML merge, resolution and tier gating

- [ ] 2.1 Merge `environments` from groups and repositories and resolve `env:` references in `yaml-config.tf`
- [ ] 2.2 Gate on subscription tier and visibility (`effective_environments`, `repos_with_skipped_environments`)
- [ ] 2.3 Extend `reviewer_team_slugs` with environment team reviewers and add `environment_reviewer_users`
- [ ] 2.4 Add the `github_user` data source and `environment_reviewer_user_ids` in `main.tf`, wire `environments`
  and `user_ids` into `module "repositories"`
- [ ] 2.5 Add `repository_environments` and `skipped_environments` outputs to `outputs.tf`

## 3. Validation

- [ ] 3.1 Add `environments` to `VALID_GROUP_KEYS` and a validator in `scripts/validate-config.py`
- [ ] 3.2 Add the free-tier warning for private repositories
- [ ] 3.3 Add `tests/test_validate_environments.py`

## 4. Tests

- [ ] 4.1 Add `tests/environments.tftest.hcl` with fixtures: merge precedence, mutual exclusion failure,
  unresolvable secret failure, tier skip
- [ ] 4.2 Extend the e2e fixture and `tests/verify_e2e.py` with an environment using a custom branch policy

## 5. Documentation

- [ ] 5.1 Add "Managing environments" to `AGENTS.md` and a section to `README.md`
- [ ] 5.2 Add an example to `config/group/default-groups.yml`

## 6. Verification

- [ ] 6.1 `terraform fmt -check -recursive`, `terraform validate`, `terraform test`
- [ ] 6.2 `pytest tests/`, `python scripts/validate-config.py`, `pre-commit run --all-files`
