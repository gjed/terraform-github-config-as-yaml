---
name: e2e-testing
description: >-
  Run and maintain this repository's end-to-end test fixture against a real GitHub test
  organization. Maintainer-only. Use when running make e2e-* targets, editing tests/e2e/,
  debugging e2e failures, or verifying module changes against live GitHub API behavior.
---

# E2E testing (maintainers)

The fixture at `tests/e2e/` is a root module (`source = "../../"`) that provisions a complete
test org exercising every module feature, then verifies live state via the GitHub API.

## Prerequisites

- A dedicated **test organization** — never point the fixture at a real org; teardown
  destroys everything it manages.
- `GITHUB_TOKEN` with admin rights on the test org.
- `tests/e2e/terraform.tfvars` (copy from `terraform.tfvars.example`): `github_org`,
  `webhook_secret`, `membership_management_enabled`.

## Lifecycle (root Makefile delegates to tests/e2e/Makefile)

```bash
make e2e-init       # terraform init in tests/e2e/
make e2e-validate   # terraform validate (no credentials needed)
make e2e-plan
make e2e-apply
make e2e-verify     # python3 tests/verify_e2e.py — asserts live GitHub state matches outputs
make e2e-destroy    # ALWAYS tear down when done; the fixture is not meant to persist
```

## Verification contract

`tests/verify_e2e.py` reads `terraform output -json` and asserts: every repo exists with
correct visibility, teams exist by slug, `subscription_warnings` and `skipped_org_rulesets`
are non-null (fixture runs on `subscription: free`), org webhook present,
`duplicate_key_warnings` null, and the subdirectory-defined repo is loaded. Exit 0 = pass.

## Rules

- Every fixture resource is named `e2e-*`; keep that prefix for new coverage.
- New module features require fixture coverage (see `openspec/specs/e2e-test-fixture/spec.md`
  for the full coverage list).
- Failures after apply are usually GitHub API eventual consistency — re-run `make e2e-verify`
  once before debugging.
- Never commit `terraform.tfvars`, state files, or plan files from `tests/e2e/`.
