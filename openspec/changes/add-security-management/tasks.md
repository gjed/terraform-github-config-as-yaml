## 1. YAML Configuration Schema

- [ ] 1.1 Add commented-out `security` section to `config/config.yml` with `security_manager_teams` example
- [ ] 1.2 Update AGENTS.md to document the new security configuration section

## 2. Terraform Config Parsing

- [ ] 2.1 Add `security_config` local in `yaml-config.tf` to extract `security` from `common_config` (defaulting to null when absent)
- [ ] 2.2 Add `security_managers_supported` local boolean gated on `is_organization` and subscription tier (`team`/`enterprise`)
- [ ] 2.3 Add `security_manager_teams` local that resolves the team slug list (empty when unsupported or unconfigured)

## 3. Terraform Resources

- [ ] 3.1 Add `data.github_organization_roles` data source in `main.tf` with conditional count (only when security managers are configured and supported)
- [ ] 3.2 Add local to extract `security_manager` role ID from the data source
- [ ] 3.3 Add `github_organization_role_team` resource with `for_each` over `security_manager_teams` using the resolved role ID

## 4. Outputs

- [ ] 4.1 Add output for security manager team assignments (list of team slugs assigned the security manager role)

## 5. Validation Script

- [ ] 5.1 Update `scripts/validate-config.py` to validate `security` section schema (optional section, `security_manager_teams` must be list of strings)
- [ ] 5.2 Add subscription tier warning when security manager teams are configured on `free` or `pro` tier

## 6. Documentation and Examples

- [ ] 6.1 Update `config/config.yml` template comments with security configuration example
- [ ] 6.2 Update `examples/consumer/` if needed to show security configuration usage

## 7. Verification

- [ ] 7.1 Run `terraform fmt` and `terraform validate` on all changed files
- [ ] 7.2 Run `pre-commit run --all-files` to check formatting and linting
- [ ] 7.3 Run `terraform plan` with security manager teams configured to verify resource creation
- [ ] 7.4 Run `terraform plan` without security section to verify no resources are created
- [ ] 7.5 Run validation script against config with and without security section
