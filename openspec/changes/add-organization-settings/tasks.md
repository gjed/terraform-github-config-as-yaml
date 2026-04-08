## 1. YAML Configuration Parsing

- [ ] 1.1 Add optional `settings:` key parsing in `yaml-config.tf` (`lookup(local.common_config, "settings", null)`)
- [ ] 1.2 Extract `org_settings_config` local (only non-null when `is_organization = true`)
- [ ] 1.3 Compute `ghas_settings_enabled` flag: true when `subscription` is `enterprise`
- [ ] 1.4 Filter GHAS-only keys out of effective settings on non-enterprise tiers
- [ ] 1.5 Collect skipped GHAS keys into `org_settings_warnings` local for output

## 2. Terraform Resource

- [ ] 2.1 Add `github_organization_settings` resource in `main.tf` (count = `org_settings_config != null ? 1 : 0`)
- [ ] 2.2 Map all supported YAML keys to resource attributes using `try()` with safe defaults
- [ ] 2.3 Apply enterprise-gated attributes only when `ghas_settings_enabled = true`
- [ ] 2.4 Suppress `members_can_create_internal_repositories` on non-enterprise tiers (requires GitHub Enterprise)

## 3. Outputs

- [ ] 3.1 Add `organization_settings_warnings` output listing skipped enterprise settings
- [ ] 3.2 Incorporate settings warnings into existing `subscription_warnings` output (or document both)

## 4. Documentation

- [ ] 4.1 Add `settings:` block with all supported keys (commented out) to `config/config.yml`
- [ ] 4.2 Update `docs/CONFIGURATION.md` with organization settings reference table
- [ ] 4.3 Add prominent ⚠️ warning about `two_factor_requirement` in docs (removes non-2FA members immediately)
- [ ] 4.4 Document which settings require Enterprise subscription

## 5. Validation Script

- [ ] 5.1 Add `settings` block schema validation to `scripts/validate-config.py`
- [ ] 5.2 Warn when enterprise-only settings are present on non-enterprise tiers
- [ ] 5.3 Warn when `two_factor_requirement: true` is set

## 6. Verification

- [ ] 6.1 Run `terraform validate` after implementation
- [ ] 6.2 Run `pre-commit run --all-files`
- [ ] 6.3 Verify `terraform plan` shows `github_organization_settings` resource when `settings:` is configured
- [ ] 6.4 Verify no resource is created when `settings:` block is absent
- [ ] 6.5 Verify no resource is created when `is_organization: false`
