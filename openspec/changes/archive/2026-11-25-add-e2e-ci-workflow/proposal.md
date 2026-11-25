## Why

The e2e fixture (`tests/e2e/`) shipped in April and has never been run. It is complete — a full
Terraform root module consuming the module under test, a config tree covering ~35 features, and a
246-line verification script — but it requires a live GitHub organization and a token that can
delete repositories, neither of which existed.

`gjed-io` now exists as a dedicated throwaway organization for this purpose, so the fixture can be
wired up and run on a schedule.

Two gaps surfaced while preparing this:

1. The fixture had no coverage for `vulnerability_alerts`, despite that being the exact resource
   whose state layout changed in v1.1.0, nor for live branch protection state. Both features
   shipped without API-level verification.
2. The README mandated a **classic** PAT with `admin:org` + `repo` + `delete_repo`. On a public
   repository, that credential is an org-wide loaded gun exposed to every workflow change.
   Research confirmed a fine-grained PAT scoped to a single organization covers every resource the
   fixture uses, including organization rulesets.

## What Changes

- Add `.github/workflows/e2e.yml`, triggered by `workflow_dispatch` and a nightly `schedule`.
  Never on `pull_request`.
- Gate the token behind a GitHub Environment (`e2e`) so it is not readable by every workflow and
  can carry protection rules.
- Always destroy, using `if: always()`, so a failed apply or verify does not strand resources in
  the organization. A `skip_destroy` dispatch input overrides this for debugging and emits a
  warning.
- Point the fixture at `gjed-io` in both places the org name is required
  (`terraform.tfvars.example` and `config/config.yml`), with instructions for forks.
- Add `skipped_branch_protections` to the fixture outputs and verify it: private repos on free
  tier are skipped, the public repo is not.
- Verify live branch protection state via the API, so the gating decision is confirmed against
  GitHub rather than only against Terraform's own output.
- Verify `vulnerability_alerts` is enabled on every repository.
- Add `tests/e2e/requirements.txt` for PyGithub, kept separate from the root requirements since it
  is only needed for a live run.
- Rewrite the token section of the README for fine-grained PATs, with the exact permission set.

## Impact

- Affected specs: `e2e-test-fixture`
- Affected code: `.github/workflows/e2e.yml` (new), `tests/verify_e2e.py`,
  `tests/e2e/outputs.tf`, `tests/e2e/README.md`, `tests/e2e/Makefile`,
  `tests/e2e/config/config.yml`, `tests/e2e/terraform.tfvars.example`,
  `tests/e2e/requirements.txt` (new)
- No change to the module itself. Nothing here affects consumers.
- Requires manual setup before the workflow can succeed: create the `e2e` environment, set
  `E2E_GITHUB_TOKEN` and `E2E_GITHUB_ORG`. The workflow fails fast with an explicit error when
  either is missing, rather than failing obscurely inside Terraform.
- Forks inherit a fixture pointing at `gjed-io`, which they cannot write to. The README documents
  the two values to change.

## Non-Goals

- Running e2e on pull requests. Fork PRs cannot read secrets, so the gate would silently skip
  exactly where it is most wanted, and the token would be exposed to arbitrary workflow edits on a
  public repository.
- Static CI for this repository (`terraform fmt`/`validate`/`tflint`/`validate-config.py`/pytest).
  That is issue #52 and has no secret requirement; it should land independently.
