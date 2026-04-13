## Why

The module has no integration test — there is no way to verify that the full stack of
features (repositories, groups, rulesets, teams, membership, webhooks, branch protections,
Actions config, org settings, partitions) works end-to-end against a real GitHub org.
`terraform validate` catches syntax; it does not catch wrong API payloads, subscription-tier
gating regressions, or merge-logic bugs that only show at apply time.

## What Changes

- New `tests/e2e/` directory: a self-contained Terraform root module that references the
  module root locally (`../../`) and provisions a complete, realistic GitHub org
- New `tests/e2e/config/` YAML fixture tree that exercises every documented feature exactly
  once, including intentional subscription-gating scenarios (free tier + private-repo
  rulesets → `subscription_warnings` fires; org ruleset on free tier → `skipped_org_rulesets`
  fires)
- New `tests/verify_e2e.py`: post-apply assertion script using the GitHub API (PyGithub)
  to confirm provisioned state matches declared config
- New `tests/e2e/Makefile`: `init / plan / apply / verify / destroy` workflow
- New `tests/e2e/README.md`: step-by-step setup guide including how to enable team-tier
  and membership testing
- New `e2e-*` targets in the root `Makefile` delegating to `tests/e2e/`

## Capabilities

### New Capabilities

- `e2e-test-fixture`: a Terraform + YAML fixture tree that provisions a full GitHub org
  and asserts its state, covering all module features in one runnable test harness

### Modified Capabilities

## Impact

- `tests/` directory (new files, no changes to existing tests)
- Root `Makefile` (new `e2e-*` targets appended; no existing targets changed)
- No changes to `*.tf` source files, `config/`, `modules/`, or `scripts/`
- Requires `PyGithub` added to test dependencies (not to `requirements.txt`)
- Requires a dedicated throwaway GitHub org and `GITHUB_TOKEN` to run
