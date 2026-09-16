## MODIFIED Requirements

### Requirement: Repository Rulesets

The system SHALL support repository rulesets for branch protection and policy enforcement.
Repository rulesets are limited to definitions with `scope: repository` or no `scope` field.
Definitions with `scope: organization` are excluded from the per-repository rulesets map and are
not available for assignment via `rulesets:` in groups or repositories. Attempting to reference an
org-scoped ruleset per-repository is a misconfiguration.

A `required_status_checks` rule SHALL apply whether or not the consumer lists any checks. The
`required_checks` parameter defaults to an empty list, because inside a typed object the attribute
always exists and `lookup()` returns its null value rather than the supplied fallback, which
`for_each` cannot accept.

#### Scenario: Apply ruleset from group

- **GIVEN** group `oss` defines `rulesets: ["main-protection"]`
- **AND** `main-protection` is defined in `rulesets.yml`
- **WHEN** a repository uses group `oss`
- **THEN** the `main-protection` ruleset is applied to the repository

#### Scenario: Ruleset with branch conditions

- **GIVEN** a ruleset targets `~DEFAULT_BRANCH`
- **WHEN** the ruleset is applied
- **THEN** the rules apply to the repository's default branch

#### Scenario: Pull request requirements

- **GIVEN** a ruleset includes a `pull_request` rule with `required_approving_review_count: 1`
- **WHEN** the ruleset is applied
- **THEN** pull requests to matching branches require at least 1 approving review

#### Scenario: Status checks listed

- **GIVEN** a ruleset includes a `required_status_checks` rule with
  `required_checks: [{ context: "ci/build" }]`
- **WHEN** the ruleset is applied
- **THEN** a `required_check` block is created for `ci/build`

#### Scenario: Status checks rule with no checks listed

- **GIVEN** a ruleset includes a `required_status_checks` rule whose parameters omit
  `required_checks`, or set it with no value
- **WHEN** `terraform plan` is executed
- **THEN** the plan succeeds
- **AND** no `required_check` blocks are created for that rule

#### Scenario: Org-scoped ruleset excluded from per-repository rulesets

- **GIVEN** `config/ruleset/` contains a ruleset with `scope: organization`
- **AND** another ruleset with no `scope` field (repo-scoped)
- **WHEN** Terraform parses the configuration
- **THEN** only the repo-scoped ruleset is available for assignment via `rulesets:` in groups/repos
- **AND** the org-scoped ruleset is not included in the per-repository rulesets map
