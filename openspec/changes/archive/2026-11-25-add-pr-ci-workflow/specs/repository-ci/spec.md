## ADDED Requirements

### Requirement: CI runs on pull requests and the default branch

The repository SHALL provide a GitHub Actions workflow that runs on every `pull_request` and on every `push` to
`main`. The workflow SHALL NOT depend on repository or environment secrets, so that it runs for pull requests from
forks.

#### Scenario: Pull request triggers CI

- **GIVEN** a pull request is opened or updated against `main`
- **WHEN** the event is delivered
- **THEN** the CI workflow runs without access to any secret

#### Scenario: Push to main triggers CI

- **GIVEN** a commit is pushed to `main`
- **WHEN** the event is delivered
- **THEN** the CI workflow runs against that commit

#### Scenario: Superseded pull request runs are cancelled

- **GIVEN** a CI run is in progress for a pull request
- **WHEN** a newer commit is pushed to the same pull request
- **THEN** the older run is cancelled

### Requirement: CI enforces the pre-commit hook set

The CI workflow SHALL contain a job named `pre-commit` that runs every hook defined in `.pre-commit-config.yaml`
against all files and fails when any hook fails or modifies a file. CI SHALL reuse the repository's hook definitions
rather than reimplement them, so local and CI gates cannot diverge. The job SHALL provide the tools those hooks
require, including Terraform and TFLint.

#### Scenario: Hook failure fails the check

- **GIVEN** a pull request introduces a formatting, lint, secret-detection, or configuration-validation violation
- **WHEN** the `pre-commit` job runs
- **THEN** the job fails and shows the diff for any auto-fixable hook

#### Scenario: Terraform validated in every root

- **GIVEN** Terraform roots exist at the repository root, under `modules/`, in `examples/consumer`, and in `tests/e2e`
- **WHEN** the `pre-commit` job runs
- **THEN** `terraform validate` is executed against each of those roots

### Requirement: CI runs the unit test suite without the e2e fixture

The CI workflow SHALL contain a job named `pytest` that runs the tests under `tests/` excluding `tests/e2e`. The e2e
fixture provisions real repositories and requires organization credentials, so it SHALL NOT run in this workflow.

#### Scenario: Unit tests gate the pull request

- **GIVEN** a pull request breaks a test under `tests/`
- **WHEN** the `pytest` job runs
- **THEN** the job fails

#### Scenario: E2E fixture is excluded

- **GIVEN** the CI workflow is running
- **WHEN** the `pytest` job selects tests
- **THEN** nothing under `tests/e2e` is collected or executed

### Requirement: CI runs with least privilege

The CI workflow SHALL declare top-level `permissions` of `contents: read` and nothing broader. Third-party actions
SHALL be referenced by version tag consistent with the repository's other workflows, so the existing dependency
update automation keeps them current.

#### Scenario: Token is read-only

- **GIVEN** the CI workflow is running
- **WHEN** a step uses the workflow token
- **THEN** the token cannot write to the repository, issues, or pull requests

### Requirement: Check names are stable and the baseline is green

The jobs SHALL keep the names `pre-commit` and `pytest`, because rulesets managed outside this repository reference
them as required status checks. The CI workflow SHALL pass on an unmodified `main`; pre-existing hook failures SHALL
be fixed or explicitly suppressed with a stated reason before the workflow is introduced, so a failing check always
indicates a regression.

#### Scenario: Unmodified main is green

- **GIVEN** the CI workflow exists on `main` with no pending changes
- **WHEN** CI runs against `main`
- **THEN** both `pre-commit` and `pytest` succeed

#### Scenario: Renaming a job is a breaking change for rulesets

- **GIVEN** a ruleset requires the `pre-commit` status check
- **WHEN** the job is renamed
- **THEN** pull requests would wait forever for the old check name, so the rename SHALL be coordinated with the ruleset
  change
