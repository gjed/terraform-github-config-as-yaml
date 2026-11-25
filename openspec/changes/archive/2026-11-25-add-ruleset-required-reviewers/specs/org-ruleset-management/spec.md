## ADDED Requirements

### Requirement: Organization Ruleset Required Reviewers

Organization rulesets SHALL support `required_reviewers` on the `pull_request` rule with the same
shape, defaults, validation and slug resolution as repository rulesets (see the
`repository-management` requirement "Ruleset Required Reviewers").

#### Scenario: Org ruleset requires a team

- **GIVEN** an org-scoped ruleset has a `pull_request` rule with
  `required_reviewers: [{ reviewer: { slug: security-team }, file_patterns: ["*"], minimum_approvals: 1 }]`
- **AND** the subscription tier supports organization rulesets
- **WHEN** `terraform apply` is executed
- **THEN** the `github_organization_ruleset` requires 1 approval from `security-team` across the
  repositories matched by its `repository_name` conditions

#### Scenario: Org ruleset on an unsupported tier

- **GIVEN** the subscription tier is `free` or `pro`
- **WHEN** an org ruleset defines `required_reviewers`
- **THEN** the ruleset is skipped as for any other org ruleset
- **AND** no team lookup is performed for its reviewers
