## ADDED Requirements

### Requirement: Ruleset Required Reviewers

The system SHALL support the `required_reviewers` parameter on the `pull_request` rule of both
repository rulesets and organization rulesets, passing it through to the corresponding provider
resource. Each entry names a reviewer team, a list of `file_patterns`, and a `minimum_approvals`
count. A `minimum_approvals` of `0` requests review without requiring it.

A reviewer SHALL be identified by exactly one of `slug` or `id`. The `type` field is optional and
defaults to `Team`, the only type GitHub supports. A `slug` SHALL be resolved to a team ID
dynamically:

- a slug that names a team defined in `config/team/` resolves from that team's managed resource, so
  the team and a ruleset that requires it can be created in the same apply;
- any other slug resolves through a `github_team` lookup, and the plan fails when the team does not
  exist.

When `required_reviewers` is omitted or null, no `required_reviewers` block is created.

#### Scenario: Reviewer by managed team slug

- **GIVEN** `config/team/` defines team `security-team`
- **AND** a repository ruleset has a `pull_request` rule with
  `required_reviewers: [{ reviewer: { slug: security-team }, file_patterns: ["*"], minimum_approvals: 1 }]`
- **WHEN** `terraform apply` is executed on a configuration that creates the team in the same run
- **THEN** the ruleset requires 1 approval from the managed `security-team` for all files
- **AND** the ruleset is created after the team

#### Scenario: Reviewer by existing team slug

- **GIVEN** team `platform` exists in the organization but is not defined in `config/team/`
- **AND** a ruleset reviewer is `{ slug: platform }`
- **WHEN** `terraform plan` is executed
- **THEN** the team ID is read with a `github_team` lookup and used as the reviewer ID

#### Scenario: Reviewer by numeric ID

- **GIVEN** a ruleset reviewer is `{ id: 1234567, type: Team }`
- **WHEN** `terraform plan` is executed
- **THEN** no team lookup is performed for that reviewer
- **AND** `1234567` is used as the reviewer ID

#### Scenario: Unknown team slug

- **GIVEN** a ruleset reviewer is `{ slug: no-such-team }` and no such team exists
- **WHEN** `terraform plan` is executed
- **THEN** the plan fails with an error identifying the missing team

#### Scenario: Optional review

- **GIVEN** an entry sets `minimum_approvals: 0`
- **WHEN** the ruleset is applied
- **THEN** the team is added to matching pull requests for visibility and approval is not required

#### Scenario: No required reviewers

- **GIVEN** a `pull_request` rule omits `required_reviewers`, or sets it with no value
- **WHEN** `terraform plan` is executed
- **THEN** the plan succeeds
- **AND** no `required_reviewers` block is created

#### Scenario: Validation rejects malformed reviewers

- **GIVEN** a ruleset has a `required_reviewers` entry that sets both `slug` and `id`, or neither
- **OR** sets a `type` other than `Team`, an empty `file_patterns`, or `minimum_approvals` outside 0-10
- **OR** lists more than 15 entries
- **WHEN** `scripts/validate-config.py` is run
- **THEN** it reports an error naming the ruleset and the offending field
