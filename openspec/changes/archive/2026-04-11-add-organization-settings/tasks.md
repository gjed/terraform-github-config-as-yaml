## 1. YAML Configuration Parsing

- [x] 1.1 Add optional `settings:` key parsing in `yaml-config.tf` (`lookup(local.common_config, "settings", null)`)
- [x] 1.2 Extract `org_settings_config` local (only non-null when `is_organization = true`)
- [x] 1.3 Compute `ghas_settings_enabled` flag: true when `subscription` is `enterprise`
- [x] 1.4 Filter GHAS-only keys out of effective settings on non-enterprise tiers
- [x] 1.5 Collect skipped GHAS keys into `org_settings_warnings` local for output

## 2. Terraform Resource

- [x] 2.1 Add `github_organization_settings` resource in `main.tf` (count = `org_settings_config != null ? 1 : 0`)
- [x] 2.2 Map all supported YAML keys to resource attributes using `try()` with safe defaults
- [x] 2.3 Apply enterprise-gated attributes only when `ghas_settings_enabled = true`
- [x] 2.4 Suppress `members_can_create_internal_repositories` on non-enterprise tiers (requires GitHub Enterprise)

## 3. Outputs

- [x] 3.1 Add `organization_settings_warnings` output listing skipped enterprise settings
- [x] 3.2 Incorporate settings warnings into existing `subscription_warnings` output (or document both)

## 4. Documentation

- [x] 4.1 Add `settings:` block with all supported keys (commented out) to `config/config.yml`
- [x] 4.2 Update `docs/CONFIGURATION.md` with organization settings reference table
- [x] 4.3 Add prominent ⚠️ warning about `two_factor_requirement` in docs (removes non-2FA members immediately)
- [x] 4.4 Document which settings require Enterprise subscription

## 5. Validation Script

- [x] 5.1 Add `settings` block schema validation to `scripts/validate-config.py`
- [x] 5.2 Warn when enterprise-only settings are present on non-enterprise tiers
- [x] 5.3 Warn when `two_factor_requirement: true` is set

## 6. Verification

- [x] 6.1 Run `terraform validate` after implementation
- [x] 6.2 Run `pre-commit run --all-files`
- [x] 6.3 Verify `terraform plan` shows `github_organization_settings` resource when `settings:` is configured
- [x] 6.4 Verify no resource is created when `settings:` block is absent
- [x] 6.5 Verify no resource is created when `is_organization: false`
