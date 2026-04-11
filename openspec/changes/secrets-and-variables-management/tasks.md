## 1. Foundation: Input variable and config loading

- [ ] 1.1 Add `secret_values` input variable (`map(string)`, sensitive) to `variables.tf`
- [ ] 1.2 Add `config/secret/` directory with commented example YAML file (mirrors `config/webhook/examples.yml` pattern)
- [ ] 1.3 Add YAML loading logic in `yaml-config.tf`: discover `config/secret/*.yml` files, load per-file, detect duplicate keys, merge into `org_secrets_config` local
- [ ] 1.4 Parse merged config into three separate locals: `org_actions_secrets`, `org_actions_variables`, `org_dependabot_secrets` (filtering by top-level key)
- [ ] 1.5 Add `env:VAR_NAME` resolution logic for org-level secrets (resolve against `var.secret_values`, same pattern as webhook secret resolution)

## 2. Organization-level resources

- [ ] 2.1 Create `org-secrets.tf` with `github_actions_organization_secret` resource (for_each over `org_actions_secrets`)
- [ ] 2.2 Add `github_actions_organization_variable` resource in `org-secrets.tf` (for_each over `org_actions_variables`)
- [ ] 2.3 Add `github_dependabot_organization_secret` resource in `org-secrets.tf` (for_each over `org_dependabot_secrets`)
- [ ] 2.4 Implement `selected_repositories` name-to-ID resolution for org-level secrets/variables (lookup against managed repos)
- [ ] 2.5 Gate all org-level resources on `local.is_organization` (skip for personal accounts)

## 3. Repository-level config merging

- [ ] 3.1 Add `merged_secrets` local in `yaml-config.tf`: merge `secrets.actions` and `secrets.dependabot` from groups (in order) with repo-level overrides
- [ ] 3.2 Add `merged_variables` local in `yaml-config.tf`: merge `variables.actions` from groups with repo-level overrides
- [ ] 3.3 Resolve `env:VAR_NAME` for repo-level secrets against `var.secret_values`
- [ ] 3.4 Add `secrets` and `variables` to the `local.repositories` output map (passed to `modules/repository/`)

## 4. Repository module: variables and resources

- [ ] 4.1 Add `secrets` and `variables` input variables to `modules/repository/variables.tf`
- [ ] 4.2 Add `github_actions_secret` resource in `modules/repository/` (for_each over `var.secrets.actions`)
- [ ] 4.3 Add `github_actions_variable` resource in `modules/repository/` (for_each over `var.variables.actions`)
- [ ] 4.4 Add `github_dependabot_secret` resource in `modules/repository/` (for_each over `var.secrets.dependabot`)

## 5. Validation

- [ ] 5.1 Add check block for `selected_repositories` references (ensure referenced repos exist in `local.repos_yaml`)
- [ ] 5.2 Add check block for undefined `env:` references (secrets referencing keys missing from `var.secret_values`)
- [ ] 5.3 Add duplicate key detection for `config/secret/` files (consistent with repo/group/ruleset pattern)
- [ ] 5.4 Update `scripts/validate-config.py` with schema validation for `config/secret/` files and repo/group-level `secrets`/`variables` keys

## 6. Consumer example and documentation

- [ ] 6.1 Update `examples/consumer/` to demonstrate `secret_values` variable usage
- [ ] 6.2 Add `config/secret/examples.yml` with commented examples for all three org-level types
- [ ] 6.3 Add commented `secrets`/`variables` examples in `config/group/default-groups.yml`
- [ ] 6.4 Update `AGENTS.md` with secrets/variables management section
- [ ] 6.5 Add outputs for managed secrets/variables (names only, not values) in `outputs.tf`

## 7. Verification

- [ ] 7.1 Run `terraform fmt -recursive` and fix formatting
- [ ] 7.2 Run `terraform validate` and fix any errors
- [ ] 7.3 Run `pre-commit run --all-files` and fix any failures
- [ ] 7.4 Run `terraform plan` against example config with secrets defined and verify expected resources
