# CI/CD examples

Copy-ready pipelines for a repository that manages a GitHub organization with this module. They are
templates: this repository does not run them, which is why they live here and not in `.github/workflows/`.
They assume the layout of [`examples/consumer`](../examples/consumer/README.md), with `main.tf` at the
repository root. If yours is in a subdirectory, change `TF_WORKING_DIR` at the top of each workflow.

## What is here

| Path                                                 | Purpose                                                                  |
| ---------------------------------------------------- | ------------------------------------------------------------------------ |
| `github-actions/terraform-pr.yml`                    | Validate and plan on pull requests; the plan is posted as one PR comment |
| `github-actions/terraform-apply.yml`                 | Apply after a merge, behind an environment approval, one run at a time   |
| `github-actions/terraform-drift.yml`                 | Nightly drift check with a full refresh; report in the job summary       |
| `jenkins/Jenkinsfile`                                | The same three behaviours as one declarative Jenkins pipeline            |
| `backends/{s3,gcs,azure,terraform-cloud}/backend.tf` | Remote state examples, one small file each                               |
| `docs/authentication.md`                             | GitHub App versus PAT, the permissions each feature needs                |

## Which one to use

- **GitHub Actions** if the configuration repository is on GitHub, which it almost always is. Nothing to
  host, and approvals use GitHub environments.
- **Jenkins** if your organization already runs Jenkins agents and wants Terraform inside that network, for
  example because the state backend is only reachable from there.

Pick one. Running both against the same state only adds lock contention.

## Behaviours

- **Plan on pull request.** Runs `terraform fmt -check`, `validate` and `plan`, and posts the plan as a
  single comment that later pushes update. The plan skips the refresh (`-refresh=false`) so it shows what
  the change does, not drift. It uses a read-only credential.
- **Apply behind an approval.** On a push to the default branch, the apply job waits for the reviewers of a
  protected environment, plans with a full refresh, and applies that plan. A plan that destroys or replaces
  a `github_repository` is refused: to offboard a repository, remove it from the state with
  `scripts/offboard-repos.sh`. Runs are serialised and a running apply is never cancelled.
- **Nightly drift.** Runs `scripts/detect-drift.sh` and fails on any non-zero exit code, so GitHub's failed
  workflow notification is the alert.

| Exit code | Meaning                                                  |
| --------- | -------------------------------------------------------- |
| 0         | No drift                                                 |
| 1         | Error (missing tool, failed plan, invalid plan JSON)     |
| 2         | Drift: the plan changes at least one resource            |
| 3         | Critical drift: a `github_repository` would be destroyed |

The workflow calls the script directly. `make drift-check` prints the same report, but GNU make turns any
failing recipe into exit status 2, so codes 2 and 3 could no longer be told apart. The plan also lists
configuration that is merged but not applied yet; a green apply workflow keeps that to a minimum.

## Setup for GitHub Actions

1. Create the GitHub Apps and the apply environment as described in
   [`docs/authentication.md`](docs/authentication.md).

1. Add the secrets and variables below.

1. Copy the workflows you want to `.github/workflows/` and replace every `PLACEHOLDER`.

1. For drift detection, copy `scripts/detect-drift.sh` and `scripts/drift_report.py` from this repository to
   your own `scripts/` directory (keep them executable). A fork of this repository already has them.

1. Add a `backend.tf` from [`backends/`](backends/) and the steps that give the runner access to it.

1. Optionally make the `plan` job a required check on the default branch so it blocks merges.

| Name                       | Kind                          | Used by        | Holds                                    |
| -------------------------- | ----------------------------- | -------------- | ---------------------------------------- |
| `TF_PLAN_APP_CLIENT_ID`    | Repository variable           | PR plan, drift | Client ID of the read-only GitHub App    |
| `TF_PLAN_APP_PRIVATE_KEY`  | Repository secret             | PR plan, drift | Private key of the read-only GitHub App  |
| `TF_APPLY_APP_CLIENT_ID`   | Repository variable           | Apply          | Client ID of the read-write GitHub App   |
| `TF_APPLY_APP_PRIVATE_KEY` | Environment secret (approved) | Apply          | Private key of the read-write GitHub App |

Add your backend credentials to the same places. Never put a token in the YAML, and never print it.

Token permissions per feature (what the Apps may do) are listed in
[`docs/authentication.md`](docs/authentication.md#minimum-app-permissions). Read-only for the plan App,
read and write for the apply App.

The workflows grant the built-in `GITHUB_TOKEN` only what each job needs: `contents: read`, plus
`pull-requests: write` for the plan comment. It is separate from the App tokens, which are the credentials
Terraform uses.

## Setup for Jenkins

1. Replace every value in `<ANGLE_BRACKETS>` in `jenkins/Jenkinsfile` (agent label, lock name, approvers,
   credential IDs, notification address, tfcmt version).

1. Create the GitHub App credential as described in [`docs/authentication.md`](docs/authentication.md).

1. Create a multibranch pipeline for the repository. The timer trigger in the file schedules the nightly
   drift run.

1. Add the backend credentials where the `PLACEHOLDER` comment in the Setup stage says.

The pipeline plans with `-refresh=false` on pull requests and merges, with a full refresh on the nightly
run (or when `FORCE_REFRESH` is ticked), holds a lock around every plan and apply, and asks for approval
before applying. It sends a `[DRIFT]` mail when a nightly plan has changes.

## Security notes

- Actions are pinned to a full commit SHA, with the version in a comment so Renovate or Dependabot can bump
  them. Keep it that way when you edit.
- The workflows use `pull_request`, never `pull_request_target`. Fork pull requests get no secrets, so the
  plan job is skipped for them.
- A plan comment shows the plan as Terraform prints it, which masks values marked sensitive. Review what
  your configuration puts in resource attributes before enabling it on a public repository.
- A saved plan file contains secrets in clear text. The apply workflow keeps it on the runner and does not
  upload it.
- The state holds secret values. Use an encrypted private backend and restrict who can read it.

## Not included

- A composite `setup-terraform` action: the three setup steps are short enough to read in place.
- A release workflow. This repository's own
  [`release.yml`](../.github/workflows/release.yml) is the reference for semantic-release.
- Slack or email integrations, and auto-remediation of drift. Drift is reported, never fixed
  automatically.
