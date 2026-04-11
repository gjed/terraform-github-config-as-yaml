# Spec Delta: Repository Management — Organization Rulesets

## MODIFIED Requirements

### Requirement: Repository Rulesets (MODIFIED)

**Original:** The system SHALL support repository rulesets for branch protection and policy enforcement.

**Modification:** Repository rulesets are limited to definitions with `scope: repository` or no
`scope` field. Definitions with `scope: organization` are excluded from the per-repository
rulesets map and are not available for assignment via `rulesets:` in groups or repositories.
Attempting to reference an org-scoped ruleset per-repository is a misconfiguration.

#### Scenario: Org-scoped ruleset excluded from per-repository rulesets

- **GIVEN** `config/ruleset/` contains a ruleset with `scope: organization`
- **AND** another ruleset with no `scope` field (repo-scoped)
- **WHEN** Terraform parses the configuration
- **THEN** only the repo-scoped ruleset is available for assignment via `rulesets:` in groups/repos
- **AND** the org-scoped ruleset is not included in the per-repository rulesets map

______________________________________________________________________

## MODIFIED Requirements (Subscription Tier Awareness)

### Requirement: Subscription Tier Awareness (MODIFIED)

**Addition:** The system SHALL skip organization-level rulesets (`scope: organization`) on `free`
and `pro` plans, and SHALL emit a `skipped_org_rulesets` output listing the names of skipped
org rulesets. Organization rulesets require a `team` or `enterprise` subscription.

The existing behaviour for repository-level rulesets on private repos is unchanged: on `free`
plans, rulesets are skipped for private repos and listed in `subscription_warnings`.

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

______________________________________________________________________

## ADDED Requirements

### Requirement: Organization Rulesets

The system SHALL support organization-level rulesets that apply rules across multiple repositories
based on repository name patterns, using `github_organization_ruleset`.

See `openspec/changes/add-org-rulesets/specs/org-ruleset-management/spec.md` for full scenarios.
