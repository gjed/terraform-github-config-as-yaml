## ADDED Requirements

### Requirement: CI Examples Directory

The repository SHALL provide a `ci/` directory at its root holding copy-ready CI/CD templates for
consumers: `ci/README.md`, `ci/github-actions/` with `terraform-pr.yml`, `terraform-apply.yml` and
`terraform-drift.yml`, `ci/jenkins/Jenkinsfile`, `ci/backends/` with S3, GCS, Azure and Terraform Cloud
`backend.tf` examples, and `ci/docs/authentication.md`. The templates SHALL NOT live under
`.github/workflows/` and SHALL NOT be run by this repository.

#### Scenario: Consumer finds the templates

- **WHEN** a consumer opens `ci/README.md`
- **THEN** it explains when to use GitHub Actions or Jenkins, lists the required secrets, variables and
  token permissions, and links every template

#### Scenario: Templates do not run on this repository

- **WHEN** this repository's workflows are listed
- **THEN** none of the example templates appears among them

### Requirement: Pull Request Plan Workflow

`ci/github-actions/terraform-pr.yml` SHALL validate the configuration and run `terraform plan` on pull
requests, post the plan as a single pull request comment that is updated on later pushes, and hold only
read access to the repository and the credential needed to plan. It SHALL NOT use `pull_request_target`
and SHALL NOT print credentials.

#### Scenario: Plan comment

- **WHEN** a pull request changes configuration
- **THEN** the workflow posts or updates one comment containing the plan

#### Scenario: Fork pull request

- **WHEN** a pull request comes from a fork
- **THEN** the plan job does not run, because secrets are not available to it

### Requirement: Gated Apply Workflow

`ci/github-actions/terraform-apply.yml` SHALL apply on push to the default branch only after the approval
required by a protected `environment:`, SHALL serialise runs with a `concurrency` group that never cancels
a running apply, and SHALL refuse to apply a plan that destroys or replaces a `github_repository`.

#### Scenario: Apply waits for approval

- **WHEN** a change is merged to the default branch
- **THEN** the apply job waits for the environment's reviewers before any credential is released

#### Scenario: Repository destroy is refused

- **WHEN** the plan deletes or replaces a `github_repository`
- **THEN** the workflow fails before `terraform apply` and explains how to offboard a repository

### Requirement: Scheduled Drift Workflow

`ci/github-actions/terraform-drift.yml` SHALL run on a schedule and on `workflow_dispatch`, call
`scripts/detect-drift.sh` directly rather than through `make`, write the markdown report to the job
summary, and fail the job for exit code `1` (error), `2` (drift) and `3` (critical drift) with an
annotation that names the meaning of the code.

#### Scenario: No drift

- **WHEN** the script exits `0`
- **THEN** the job succeeds and the summary holds the no-drift report

#### Scenario: Critical drift

- **WHEN** the script exits `3`
- **THEN** the job fails with an error annotation that a repository would be destroyed or replaced

### Requirement: Pinned Actions and Least Privilege

Every `uses:` in the example workflows SHALL reference a full 40-character commit SHA followed by a
`# vX.Y.Z` comment, every workflow SHALL declare minimal `permissions:`, and none SHALL use
`pull_request_target`.

#### Scenario: Unpinned action

- **WHEN** a workflow references an action by tag or branch
- **THEN** the test suite fails

### Requirement: Jenkins Pipeline Template

`ci/jenkins/Jenkinsfile` SHALL be a declarative pipeline that plans with `-refresh=false` on pull requests
and merges and with a full refresh on the nightly trigger, serialises Terraform runs with a lock, applies
only after an `input` approval, refuses a plan that destroys or replaces a `github_repository`, and sends a
`[DRIFT]` notification when the nightly plan has changes. Every site-specific value SHALL be a clearly
marked placeholder.

#### Scenario: Nightly run

- **WHEN** the timer trigger starts the pipeline
- **THEN** the plan refreshes state, the Apply stage is skipped, and changes in the plan raise a
  `[DRIFT]` notification

### Requirement: Backend Examples

`ci/backends/` SHALL contain a small commented `backend.tf` example for each of S3, GCS, Azure and
Terraform Cloud, with no real credentials.

#### Scenario: Pick a backend

- **WHEN** a consumer copies one backend example
- **THEN** it holds a single `terraform` block whose values are placeholders

### Requirement: Authentication Guide

`ci/docs/authentication.md` SHALL explain why a GitHub App installation token is preferred over a personal
access token, list the minimum App permissions per module feature, show how to pass the token to the
provider as `GITHUB_TOKEN`, and state that the token must never appear in logs.

#### Scenario: Least-privilege setup

- **WHEN** a consumer uses only repositories and rulesets
- **THEN** the guide shows which App permissions that requires and that the others can be left off

### Requirement: Consumer README Link

`examples/consumer/README.md` SHALL link to the scheduled drift workflow in `ci/github-actions/` and to
`ci/README.md`, and SHALL state that `scripts/detect-drift.sh` and `scripts/drift_report.py` must be copied
into the consumer repository.

#### Scenario: Consumer wants drift detection

- **WHEN** a consumer reads `examples/consumer/README.md`
- **THEN** it points at the drift workflow template and names the scripts to copy

### Requirement: Example Validation

The repository SHALL include a test that parses every YAML file under `ci/` and under
`examples/consumer/.github/workflows/` when that directory exists, asserts that every `uses:` is pinned to
a 40-character SHA, that no workflow uses `pull_request_target`, and that the drift workflows call
`scripts/detect-drift.sh` and not `make drift-check`.

#### Scenario: Drift workflow calls make

- **WHEN** a drift workflow runs `make drift-check`
- **THEN** the test fails
