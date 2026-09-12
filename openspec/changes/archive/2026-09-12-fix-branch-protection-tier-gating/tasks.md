## 1. Add tier gating locals

- [x] 1.1 Add `branch_protections_require_paid_for_private` next to `rulesets_require_paid_for_private`
- [x] 1.2 Add `effective_branch_protections` filtering private repos on `free`
- [x] 1.3 Add `repos_with_skipped_branch_protections`
- [x] 1.4 Replace the `merged_branch_protections` reference in `repo_configs` with `effective_branch_protections`
- [x] 1.5 Correct the inaccurate comment above `merged_branch_protections`

## 2. Surface skipped protections

- [x] 2.1 Add `skipped_branch_protections` output mirroring `skipped_org_rulesets`
- [x] 2.2 Leave `subscription_warnings` shape unchanged (ruleset-only, no consumer break)

## 3. Pre-plan validation

- [x] 3.1 Warn in `validate-config.py` when private repos on `free` have branch protections
- [x] 3.2 Resolve effective visibility through group inheritance, not just the repo-level key

## 4. Tests

- [x] 4.1 Test: free + private + branch protections → warning
- [x] 4.2 Test: free + public + branch protections → no warning
- [x] 4.3 Test: paid tier + private + branch protections → no warning
- [x] 4.4 Test: visibility inherited from group is resolved correctly

## 5. Verify

- [x] 5.1 `terraform validate` passes
- [x] 5.2 Full pytest suite passes (43 tests, 15 new)
- [x] 5.3 `pre-commit run --all-files` clean for touched files
- [x] 5.4 `openspec validate fix-branch-protection-tier-gating --strict` passes

## 6. Verification evidence

Confirmed against the real e2e fixture (`tests/e2e/config`, `subscription: free`):

- `terraform console` → `local.repos_with_skipped_branch_protections` returns
  `["e2e-internal-private", "e2e-multi-group"]`
- `local.effective_branch_protections` drops both to `0` protections while the public
  `e2e-full-featured` retains its `1`
- `validate_branch_protection_tier` emits exactly 2 warnings, naming the same two repositories

## 7. Follow-up (out of scope, filed separately)

- [x] 7.1 `yamldecode` fails on comment-only YAML files with "missing start of document".
      Affects `config/membership/example-members.yml` (the module's own shipped template) and
      `tests/e2e/config/membership/test-members.yml`. `local.membership_config` at
      `yaml-config.tf:300` explicitly expects null for comment-only files, but `yamldecode`
      errors before the null check is reached, so `terraform plan` aborts. Pre-existing on
      `origin/main`; blocks the e2e fixture independently of branch protection gating.
      Resolved separately by change `fix-yamldecode-comment-only-yaml` (PR #60, released
      in v1.3.0).
