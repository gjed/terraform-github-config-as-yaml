## 1. YAML Parsing and Resolution

- [x] 1.1 Add `org_webhook_names` local that reads `org_webhooks` list from
  `local.common_config` (default `[]`)
- [x] 1.2 Add `resolved_org_webhooks` local that looks up each name in `local.webhooks_config`,
  normalizes types, and resolves `env:VAR_NAME` secrets via `var.webhook_secrets`
- [x] 1.3 Guard org webhook resolution with `local.is_organization` (empty map for personal
  accounts)
- [x] 1.4 Verify: `terraform plan` with org webhooks defined produces expected resource count;
  plan with no `org_webhooks` key produces zero resources

## 2. Terraform Resource

- [x] 2.1 Add `github_organization_webhook.this` resource in `main.tf` with
  `for_each = local.resolved_org_webhooks`
- [x] 2.2 Map configuration block: url, content_type, secret (sensitive), insecure_ssl
- [x] 2.3 Map events list and active flag
- [x] 2.4 Verify: `terraform plan` shows correct create/update/destroy for org webhook changes

## 3. Outputs

- [x] 3.1 Add `org_webhooks` output in `outputs.tf` (map of webhook names to URLs)
- [x] 3.2 Verify: output is empty map when no org webhooks configured

## 4. Config Template

- [x] 4.1 Add `org_webhooks` example (commented out) to `config/config.yml` template
- [x] 4.2 Add example org webhook definition to `config/webhook/` template directory

## 5. Validation

- [x] 5.1 Update `scripts/validate-config.py` to validate `org_webhooks` references resolve to
  defined webhooks
- [x] 5.2 Update `scripts/validate-config.py` to warn when `org_webhooks` is set but
  `is_organization` is false
- [x] 5.3 Verify: validation script catches undefined org webhook references

## 6. Documentation

- [x] 6.1 Update AGENTS.md with org webhook configuration guidance
- [x] 6.2 Add org webhooks section to consumer example comments
- [x] 6.3 Document that org webhooks fire for ALL repos in the org
