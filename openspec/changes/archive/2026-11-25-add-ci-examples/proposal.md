## Why

Consumers of the module have to invent their own CI/CD: how to review a plan on a pull request, how to
apply it behind an approval, how to run drift detection on a schedule, and how to give Terraform a GitHub
credential without leaking it. The module now ships a drift script with a documented exit-code contract,
but nothing shows how to wire it into a pipeline. Issue #10 asks for ready-to-copy examples.

## What Changes

- Add a `ci/` folder at the repository root with copy-ready templates (not run by this repository):
  - `ci/README.md`: overview, when to use GitHub Actions or Jenkins, required secrets and token permissions
  - `ci/github-actions/terraform-pr.yml`: validate and plan on pull requests, plan posted as a PR comment
  - `ci/github-actions/terraform-apply.yml`: apply on push to the default branch behind a protected
    `environment:`, serialised, refusing a plan that destroys or replaces a `github_repository`
  - `ci/github-actions/terraform-drift.yml`: scheduled drift run calling `scripts/detect-drift.sh` and
    honouring its exit codes
  - `ci/jenkins/Jenkinsfile`: declarative pipeline with the same behaviours
  - `ci/backends/`: `backend.tf` examples for S3, GCS, Azure and Terraform Cloud
  - `ci/docs/authentication.md`: GitHub App token versus PAT, minimum App permissions per module feature
- Link the drift workflow from `examples/consumer/README.md` instead of copying it: a copy under
  `examples/consumer/.github/workflows/` would be byte for byte identical and would drift apart over time
- Add a "CI/CD examples" section to `README.md` and `AGENTS.md`
- Add `tests/test_ci_examples.py`, which parses every example workflow and asserts the supply-chain rules

Not included: a composite `setup-terraform` action, a `release.yml` example (this repository's own
`.github/workflows/release.yml` is the reference), Slack or email integrations, auto-remediation, and any
change to this repository's own `.github/workflows/`.

## Capabilities

### New Capabilities

- `ci-examples`: Example CI/CD pipelines for consumers: GitHub Actions and Jenkins templates for PR plan,
  gated apply and scheduled drift detection, backend examples, and authentication guidance.

### Modified Capabilities

(none)

## Impact

- New files only, plus documentation links in `README.md`, `AGENTS.md` and `examples/consumer/README.md`
- No Terraform, module, script or workflow behaviour changes; the examples live outside
  `.github/workflows/`, so GitHub never runs them on this repository
- One new test file, run by the existing `pytest` job
