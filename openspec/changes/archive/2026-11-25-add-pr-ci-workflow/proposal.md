# Proposal

## Why

This module is published to the Terraform Registry, so a broken `main` ships to consumers. Every quality gate
(`terraform fmt`/`validate`, `tflint`, `checkov`, `detect-secrets`, `markdownlint`, `yamllint`,
`scripts/validate-config.py`, and the `tests/` pytest suite) runs only through `pre-commit` on a contributor's machine.
Nothing runs on a pull request, so a contributor who skips or bypasses `pre-commit` has no backstop. The existing
workflows cover only releases (`release.yml`) and the live-organization e2e fixture (`e2e.yml`, never on PRs).

Tracked as [#52](https://github.com/gjed/terraform-github-config-as-yaml/issues/52).

## What Changes

- Add `.github/workflows/ci.yml`, triggered on `pull_request` and on `push` to `main`, with two jobs: `pre-commit`
  (runs the repository's own hook set, so CI cannot drift from local gates) and `pytest` (runs `tests/` excluding
  `tests/e2e`).
- Run with read-only `contents` permission and no secrets, so the workflow is safe for fork PRs.
- Cache pip and pre-commit environments.
- Clear the pre-existing hook failures so the first run on `main` is green (separate prerequisite PR, no spec impact):
  trailing whitespace, `detect-secrets` and `checkov` false positives in the e2e fixture, and `markdownlint` debt in
  `openspec/` and `docs/`.
- Out of scope: making the check required on `main`. That is a ruleset change managed in the separate Terraform
  repository that owns this repository's settings, and it can only be done once the check has run green.
- Out of scope: the e2e workflow, which already exists and must stay off the `pull_request` trigger.

## Capabilities

### New Capabilities

- `repository-ci`: continuous-integration gate for this repository's own pull requests and default branch — which
  checks run, when, with what privileges, and the stability of check names that rulesets depend on.

### Modified Capabilities

None. `release-automation` and `e2e-test-fixture` are unchanged.

## Impact

- New file: `.github/workflows/ci.yml`.
- Prerequisite lint fixes touch `openspec/**`, `docs/RESEARCH.md`, `tests/e2e/**` and `.github/workflows/e2e.yml`
  (formatting and inline suppressions only).
- No change to module inputs, outputs, or resources; no release impact (`ci:` commit type).
- Follow-up outside this repository: add `pre-commit` and `pytest` as required status checks in the ruleset for
  `main`.
