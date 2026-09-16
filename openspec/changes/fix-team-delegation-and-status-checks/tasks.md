## 1. Delegation algorithm casing

- [x] 1.1 Verify the provider's accepted values by applying against a real organization
- [x] 1.2 Accept both casings in `modules/team/variables.tf` validation
- [x] 1.3 Normalise to uppercase in `modules/team/main.tf`
- [x] 1.4 Compare case-insensitively in `scripts/validate-config.py`
- [x] 1.5 Correct `examples/consumer/config/team/engineering.yml`

## 2. Status check parameter default

- [x] 2.1 Default `required_checks` to `[]` in `modules/repository/variables.tf`
- [x] 2.2 Guard the typed `for_each` in `modules/repository/main.tf`
- [x] 2.3 Guard the org-level `for_each` in `main.tf` against null from YAML

## 3. Fixture corrections

- [x] 3.1 `member_count: 0` to `1` in `tests/e2e/config/team/test-teams.yml`
- [x] 3.2 `required_status_checks:` to `required_checks:` in
  `tests/e2e/config/ruleset/test-rulesets.yml`

## 4. Tests and verification

- [x] 4.1 Add `tests/test_validate_delegation.py`
- [x] 4.2 Full suite passes (63 tests)
- [x] 4.3 `terraform validate` passes
- [x] 4.4 `terraform plan` against `gjed-io` succeeds: 45 to add, 0 errors
- [x] 4.5 Live e2e run green end to end — completed in fix-actions-tier-conflict after two more
  bugs surfaced by the same run (org/repo actions tier conflict, nested team privacy); apply
  succeeded (45 resources), `verify_e2e.py` reported 33/33, destroy cleaned up completely

## 5. Follow-ups

- [x] 5.1 Added `--config-dir` to `scripts/validate-config.py` in fix-actions-tier-conflict —
  the script previously had no flag to target a config directory, so it silently validated
  `config/` even when pointed at the fixture.
