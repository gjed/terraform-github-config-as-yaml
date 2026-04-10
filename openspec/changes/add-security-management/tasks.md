## 1. YAML Configuration Schema

- [x] 1.1 Add commented-out `security` section to `config/config.yml` with `security_manager_teams` example
- [x] 1.2 Update AGENTS.md to document the new security configuration section

## 2. Terraform Config Parsing

- [x] 2.1 Add `security_config` local in `yaml-config.tf` to extract `security` from `common_config` (defaulting to null when absent)
- [x] 2.2 Add `security_managers_supported` local boolean gated on `is_organization` and subscription tier (`team`/`enterprise`)
- [x] 2.3 Add `security_manager_teams` local that resolves the team slug list (empty when unsupported or unconfigured)

## 3. Terraform Resources

- [x] 3.1 Add `data.github_organization_roles` data source in `main.tf` with conditional count (only when security managers are configured and supported)
- [x] 3.2 Add local to extract `security_manager` role ID from the data source
- [x] 3.3 Add `github_organization_role_team` resource with `for_each` over `security_manager_teams` using the resolved role ID

## 4. Outputs

- [x] 4.1 Add output for security manager team assignments (list of team slugs assigned the security manager role)

## 5. Validation Script

- [x] 5.1 Update `scripts/validate-config.py` to validate `security` section schema (optional section, `security_manager_teams` must be list of strings)
- [x] 5.2 Add subscription tier warning when security manager teams are configured on `free` or `pro` tier

## 6. Documentation and Examples

- [x] 6.1 Update `config/config.yml` template comments with security configuration example
- [x] 6.2 Update `examples/consumer/` if needed to show security configuration usage

## 7. Verification

- [x] 7.1 Run `terraform fmt` and `terraform validate` on all changed files
- [x] 7.2 Run `pre-commit run --all-files` to check formatting and linting
- [x] 7.3 Run `terraform plan` with security manager teams configured to verify resource creation
- [x] 7.4 Run `terraform plan` without security section to verify no resources are created
- [x] 7.5 Run validation script against config with and without security section
