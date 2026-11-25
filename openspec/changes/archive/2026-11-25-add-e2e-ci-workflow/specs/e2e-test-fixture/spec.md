## ADDED Requirements

### Requirement: E2E fixture runs in CI on a schedule

A workflow at `.github/workflows/e2e.yml` SHALL run the e2e fixture end to end: `init`,
`validate`, `plan`, `apply`, verify, then `destroy`.

The workflow SHALL be triggered by `workflow_dispatch` and by a nightly `schedule`. It SHALL
NOT be triggered by `pull_request`. Fork pull requests cannot read repository secrets, so a
pull-request trigger would silently skip the run, and exposing a token that can delete
repositories to arbitrary workflow edits on a public repository is not acceptable.

The credentials SHALL be held in a GitHub Environment named `e2e`, so they are not readable by
every workflow in the repository and can carry environment protection rules. The workflow SHALL
read the token from `secrets.E2E_GITHUB_TOKEN` and the target organization from
`vars.E2E_GITHUB_ORG`.

The workflow SHALL declare a `concurrency` group that queues rather than cancels, because two
concurrent runs would contend for the same repositories in the test organization and a
cancelled run would strand resources.

#### Scenario: Nightly run provisions, verifies, and destroys

- **WHEN** the scheduled trigger fires
- **THEN** the fixture is applied against the configured organization
- **AND** `tests/verify_e2e.py` runs against the live GitHub API
- **AND** all provisioned resources are destroyed before the job finishes

#### Scenario: Destroy runs even when apply or verify fails

- **GIVEN** `terraform apply` or the verification step exits non-zero
- **WHEN** the job reaches the destroy step
- **THEN** `terraform destroy` still runs, because the step is conditioned on `always()`
- **AND** no `e2e-*` resources are left behind in the organization

#### Scenario: Debug run may retain resources

- **GIVEN** the workflow is dispatched manually with `skip_destroy` set to true
- **WHEN** the run completes
- **THEN** the destroy step is skipped
- **AND** a warning annotation reports that resources remain and must be removed manually

#### Scenario: Missing configuration fails fast

- **GIVEN** `secrets.E2E_GITHUB_TOKEN` or `vars.E2E_GITHUB_ORG` is not set
- **WHEN** the workflow runs
- **THEN** it fails at the first step with an error naming the missing value
- **AND** no Terraform command is executed

#### Scenario: Pull requests do not trigger the fixture

- **WHEN** a pull request is opened or updated
- **THEN** the e2e workflow does not run

### Requirement: Fixture targets a dedicated organization by default

The committed fixture configuration SHALL name the organization used by this repository's CI in
both places the value is required: `github_org` in `tests/e2e/terraform.tfvars.example` and
`organization` in `tests/e2e/config/config.yml`.

The README SHALL state that forks must change both values to their own throwaway organization
before running the fixture.

#### Scenario: Fixture is runnable without editing placeholders

- **WHEN** a maintainer copies `terraform.tfvars.example` to `terraform.tfvars`
- **THEN** no placeholder substitution is required to run against this repository's test org

#### Scenario: Fork is told which values to change

- **WHEN** a contributor working on a fork reads `tests/e2e/README.md`
- **THEN** the README names both files that must be updated to point at their own organization

### Requirement: Verification asserts branch protection tier gating

`tests/verify_e2e.py` SHALL assert that the `skipped_branch_protections` output matches the
subscription tier.

On `free`, the output SHALL be non-null and SHALL list every private repository that has branch
protections, and SHALL NOT list public repositories. On a paid tier, the output SHALL be null.

The script SHALL additionally confirm the decision against the GitHub API rather than relying
only on Terraform's own output: a public repository with branch protections SHALL report its
default branch as protected, and a repository reported as skipped SHALL report its default
branch as unprotected.

A repository with no default branch yet SHALL NOT be treated as a failure, since there is no
branch to protect.

#### Scenario: Free tier skips private repositories

- **GIVEN** the fixture runs with `subscription: free`
- **WHEN** verification runs
- **THEN** `skipped_branch_protections` lists `e2e-internal-private` and `e2e-multi-group`
- **AND** it does not list the public `e2e-full-featured`

#### Scenario: Live state matches the gating decision

- **GIVEN** `skipped_branch_protections` lists a repository
- **WHEN** the GitHub API is queried for that repository's default branch
- **THEN** the branch reports `protected: false`
- **AND** the public repository's default branch reports `protected: true`

#### Scenario: Empty repository is not a failure

- **GIVEN** a repository has been created but has no commits, so no default branch exists
- **WHEN** verification queries its branch protection state
- **THEN** the check passes without asserting protection state

### Requirement: Verification asserts vulnerability alerts

`tests/verify_e2e.py` SHALL assert that Dependabot vulnerability alerts are enabled on every
repository in the `repositories` output, since every fixture repository inherits
`vulnerability_alerts: true` from its group.

This covers `github_repository_vulnerability_alerts`, which replaced the deprecated inline
repository argument and was otherwise unverified.

#### Scenario: Alerts enabled on every fixture repository

- **WHEN** verification runs after a successful apply
- **THEN** each repository reports vulnerability alerts as enabled via the GitHub API

### Requirement: Verification dependencies are declared

A `requirements.txt` at `tests/e2e/` SHALL declare the Python dependencies needed by
`tests/verify_e2e.py`. It SHALL be kept separate from the repository root `requirements.txt`,
because those dependencies are only needed for a live fixture run and not for pre-commit or the
unit test suite.

#### Scenario: Dependencies install from a declared file

- **WHEN** `pip install -r tests/e2e/requirements.txt` is run
- **THEN** PyGithub is installed and `tests/verify_e2e.py` can be executed

## MODIFIED Requirements

### Requirement: Setup is documented

A `README.md` at `tests/e2e/` SHALL document: prerequisites (test org, GitHub token,
webhook.site URLs), step-by-step run instructions, a feature coverage table, how to
enable team-tier testing (change `subscription` + upgrade org), and how to test membership
management.

The token section SHALL specify a **fine-grained** personal access token scoped to the test
organization, and SHALL enumerate the exact organization and repository permissions required. A
classic token SHALL NOT be presented as the recommended option, because it grants access to
every organization the holder belongs to and this token can delete repositories.

The prerequisites SHALL state which features are skipped on a free-tier organization —
organization rulesets, and branch protections on private repositories — and that verification
asserts those skips, so a free-tier organization is a valid configuration rather than a
degraded one.

#### Scenario: New contributor can follow README without prior knowledge

- **WHEN** a developer reads `tests/e2e/README.md`
- **THEN** they can set up and run the full E2E test without consulting any other document

#### Scenario: Token permissions are copyable

- **WHEN** a developer creates the token described in the README
- **THEN** the listed permissions are sufficient for apply, verify, and destroy
- **AND** no permission beyond the test organization is requested
