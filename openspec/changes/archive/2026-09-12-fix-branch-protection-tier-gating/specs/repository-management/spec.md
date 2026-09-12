## MODIFIED Requirements

### Requirement: Subscription Tier Awareness

The system SHALL respect GitHub subscription tier limitations when applying rulesets and branch
protections.

The system SHALL skip organization-level rulesets (`scope: organization`) on `free` and `pro`
plans, and SHALL emit a `skipped_org_rulesets` output listing the names of skipped org rulesets.
Organization rulesets require a `team` or `enterprise` subscription.

The existing behaviour for repository-level rulesets on private repos is unchanged: on `free`
plans, rulesets are skipped for private repos and listed in `subscription_warnings`.

The system SHALL skip branch protections for private repositories on the `free` plan, because
GitHub does not offer protected branches on private repositories at that tier. Skipped
repositories SHALL be listed in a `skipped_branch_protections` output. Branch protections on
public repositories are unaffected at every tier, and branch protections on private repositories
are applied normally on `pro`, `team`, and `enterprise`.

Effective visibility for this decision SHALL be resolved after group inheritance, so a repository
that inherits `visibility: private` from a group is treated the same as one that declares it
directly.

`subscription_warnings` SHALL retain its existing ruleset-only meaning and shape. Branch
protection skips are reported through the separate `skipped_branch_protections` output so that
consumers reading `subscription_warnings` are not broken.

#### Scenario: Free tier private repository

- **GIVEN** `subscription: free` is configured
- **AND** a private repository has rulesets defined
- **WHEN** Terraform is planned
- **THEN** rulesets are skipped for the private repository
- **AND** a warning is output indicating rulesets require a paid plan

#### Scenario: Paid tier private repository

- **GIVEN** `subscription: team` is configured
- **AND** a private repository has rulesets defined
- **WHEN** Terraform is planned
- **THEN** rulesets are applied to the private repository

#### Scenario: Free tier — org rulesets skipped with output

- **GIVEN** `subscription: free` is configured in `config.yml`
- **AND** at least one org ruleset (`scope: organization`) is defined
- **WHEN** `terraform plan` is executed
- **THEN** no `github_organization_ruleset` resources are planned
- **AND** the `skipped_org_rulesets` output contains the names of the skipped org rulesets

#### Scenario: Pro tier — org rulesets skipped

- **GIVEN** `subscription: pro` is configured
- **AND** at least one org ruleset is defined
- **WHEN** `terraform plan` is executed
- **THEN** no `github_organization_ruleset` resources are planned

#### Scenario: Team tier — org rulesets applied

- **GIVEN** `subscription: team` is configured
- **AND** at least one org ruleset is defined
- **WHEN** `terraform apply` is executed
- **THEN** `github_organization_ruleset` resources are created for all org rulesets
- **AND** `skipped_org_rulesets` output is null

#### Scenario: Enterprise tier — org rulesets applied

- **GIVEN** `subscription: enterprise` is configured
- **WHEN** `terraform apply` is executed
- **THEN** all org rulesets are created without restriction

#### Scenario: Free tier — branch protections skipped on private repository

- **GIVEN** `subscription: free` is configured
- **AND** a private repository has `branch_protections` defined
- **WHEN** `terraform plan` is executed
- **THEN** no `github_branch_protection` resources are planned for that repository
- **AND** the `skipped_branch_protections` output lists the repository

#### Scenario: Free tier — branch protections applied on public repository

- **GIVEN** `subscription: free` is configured
- **AND** a public repository has `branch_protections` defined
- **WHEN** `terraform plan` is executed
- **THEN** the branch protections are planned normally
- **AND** the repository is absent from `skipped_branch_protections`

#### Scenario: Paid tier — branch protections applied on private repository

- **GIVEN** `subscription: pro` is configured
- **AND** a private repository has `branch_protections` defined
- **WHEN** `terraform plan` is executed
- **THEN** the branch protections are planned normally
- **AND** the `skipped_branch_protections` output is null

#### Scenario: Free tier — visibility inherited from group

- **GIVEN** `subscription: free` is configured
- **AND** a group sets `visibility: private`
- **AND** a repository belongs to that group without declaring its own visibility
- **AND** the repository has `branch_protections` defined
- **WHEN** `terraform plan` is executed
- **THEN** the branch protections are skipped for that repository
- **AND** the repository is listed in `skipped_branch_protections`

#### Scenario: Validation warns before plan

- **GIVEN** `subscription: free` is configured
- **AND** a private repository has `branch_protections` defined
- **WHEN** `scripts/validate-config.py` is run
- **THEN** a warning reports that branch protections will be skipped for that repository
- **AND** the warning names the repository
