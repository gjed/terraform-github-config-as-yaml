## Context

The reference pipeline (a production Jenkins setup managing a real organization with this module) plans on
pull requests and merges without refreshing, plans with a full refresh nightly, gates the apply behind an
approval, notifies on drift, and fails any plan that deletes a repository. This change generalises those
behaviours into templates for GitHub Actions and Jenkins. The repository's own CI (`ci.yml`, `e2e.yml`,
`release.yml`) already covers its quality gates and is not part of this change.

## Goals / Non-Goals

**Goals:**

- Templates a consumer can copy and adapt in minutes, with every site-specific value clearly marked
- Safe by default: pinned actions, minimal `permissions:`, no secret in logs, no `pull_request_target`
- The drift workflow honours the exit codes of `scripts/detect-drift.sh`

**Non-Goals:**

- A composite `setup-terraform` action, a `release.yml` example, Slack or email integrations,
  auto-remediation
- Running any of these workflows against this repository

## Decisions

### Templates live in `ci/`, outside `.github/workflows/`

GitHub only runs workflows under `.github/workflows/`, so the templates never run here, and the ruleset
that requires this repository's own job names is untouched. The consumer example links to the
drift template instead of carrying a byte-identical copy, because the consumer layout (`main.tf` at the
repository root) is exactly what the template assumes.

### Two GitHub Apps: a read-only one for plans, a write one for apply

Any contributor who can push a branch controls the Terraform code that runs in the PR plan job, so that
job must not hold a credential that can change the organization. Plans and drift runs use a read-only App
whose key is a repository secret. Apply uses a write App whose key is an environment secret, released only
after the environment's reviewers approve and only on the allowed branch. A single PAT or App is documented
as a simpler alternative with its trade-off.

### Apply plans and applies in one job

A saved plan file contains sensitive values in clear text, so uploading it as an artifact to hand it to a
second job would put secrets where anyone with read access can download them. The environment gate sits in
front of the single job; the pull request plan comment is what the approver reviews. The job still plans
with a full refresh and applies that exact plan file, and refuses it first when it would destroy or replace
a `github_repository`.

### Drift workflow calls the script directly

GNU make turns any failing recipe into exit status 2, so `make drift-check` cannot tell drift (2) from
critical drift (3) or an error (1). The workflow runs `scripts/detect-drift.sh`, writes the markdown report
to the job summary and fails the job on any non-zero code, with an annotation that names the meaning.

### Plan comment is upserted, not appended

The PR workflow marks its comment with a hidden HTML marker and updates it on each push, so a pull request
carries one plan comment rather than one per push. The comment is truncated below GitHub's size limit.

### Jenkins stays generic

The Jenkinsfile uses built-in steps (`lock`, `input`, `mail`) and placeholders such as `<AGENT_LABEL>` and
`<GITHUB_APP_CREDENTIAL_ID>`. It does not load a shared library.

## Risks / Trade-offs

- A consumer may copy a workflow without the App setup and see a token-minting failure. The README lists
  the required secrets and variables, and the workflows fail at the token step with a clear action name.
- The permission table follows the provider's resources at the time of writing; a new module feature may
  need a new App permission. The authentication guide says to confirm against the first plan.
- `scripts/detect-drift.sh` and `scripts/drift_report.py` live in this repository, not in the module
  package. Consumers who use the module from the registry must copy both scripts into their own repository;
  the README and the workflow header say so.
