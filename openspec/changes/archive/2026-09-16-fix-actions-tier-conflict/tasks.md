## 1. Validator

- [x] 1.1 Reproduce the 409 empirically against a live org, isolated from Terraform
- [x] 1.2 Add `validate_actions_tier_conflict()` to `scripts/validate-config.py`
- [x] 1.3 Wire it into `main()` as an error (not a warning)
- [x] 1.4 Add regression tests in `tests/test_validate_actions_tier_conflict.py`

## 2. Fixture corrections

- [x] 2.1 `tests/e2e/config/config.yml`: org `allowed_actions` `selected` → `all`
- [x] 2.2 `tests/e2e/config/team/test-teams.yml`: `e2e-api` `privacy` `secret` → `closed`

## 3. Verification

- [x] 3.1 `terraform apply` against `gjed-io` succeeds (45 resources)
- [x] 3.2 `tests/verify_e2e.py` reports 33/33 checks passed
- [x] 3.3 `terraform destroy` cleans up completely (confirmed via `gh api orgs/gjed-io/repos`
  and `.../teams`)
- [x] 3.4 Full pytest suite passes
