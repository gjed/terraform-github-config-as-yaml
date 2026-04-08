# Spec Delta: Organization Ruleset Management

## ADDED Requirements

### Requirement: Organization Rulesets

The system SHALL support organization-level rulesets that apply rules across multiple repositories
based on repository name patterns, using `github_organization_ruleset`.

A ruleset definition in `config/ruleset/` with `scope: organization` is treated as an
organization-level ruleset. Definitions without a `scope` field, or with `scope: repository`,
are treated as repository-level rulesets (existing behavior).

Organization rulesets are not assignable per-repository or per-group. They are applied globally
at the organization level and filtered only by `repository_name` conditions within the ruleset
definition itself.

Organization rulesets require a `team` or `enterprise` GitHub subscription. On `free` or `pro`
plans, all org rulesets are skipped with a warning output.

#### Scenario: Org ruleset applies across repositories by name pattern

- **GIVEN** `config/ruleset/org-rulesets.yml` defines:
  ```yaml
  org-main-protection:
    scope: organization
    target: branch
    enforcement: active
    conditions:
      ref_name:
        include: ["~DEFAULT_BRANCH"]
        exclude: []
      repository_name:
        include: ["*"]
        exclude: ["sandbox-*"]
    rules:
      - type: deletion
  ```
- **WHEN** `terraform apply` is executed
- **THEN** `github_organization_ruleset.this["org-main-protection"]` is created
- **AND** the ruleset applies to all repositories except those matching `sandbox-*`

#### Scenario: Repo rulesets are unaffected by org rulesets

- **GIVEN** `config/ruleset/` contains both org-scoped and repo-scoped rulesets
- **WHEN** Terraform parses the configuration
- **THEN** repo-scoped rulesets are available for assignment via `rulesets:` in groups and repos
- **AND** org-scoped rulesets are excluded from the repo-level rulesets map

#### Scenario: Org ruleset with bypass actors

- **GIVEN** an org ruleset defines `bypass_actors` with a team actor
- **WHEN** `terraform apply` is executed
- **THEN** the bypass actors are configured on the `github_organization_ruleset` resource

#### Scenario: Org ruleset without repository_name conditions

- **GIVEN** an org ruleset omits the `repository_name` conditions block
- **WHEN** Terraform processes the configuration
- **THEN** the org ruleset applies to all repositories (no repository name filtering)

#### Scenario: Org ruleset with all supported rule types

- **GIVEN** an org ruleset uses rule types: `deletion`, `non_fast_forward`, `pull_request`,
  `required_status_checks`, `required_linear_history`, `required_signatures`,
  `branch_name_pattern`, `commit_message_pattern`
- **WHEN** `terraform apply` is executed
- **THEN** all specified rules are applied to the org ruleset

---

## ADDED Requirements

### Requirement: Organization Ruleset Subscription Gating

The system SHALL skip organization-level rulesets when the configured subscription tier is `free`
or `pro`, and SHALL emit a warning output listing skipped org rulesets.

Organization rulesets require a `team` or `enterprise` GitHub subscription.

#### Scenario: Free tier — org rulesets skipped

- **GIVEN** `subscription: free` is configured in `config.yml`
- **AND** at least one org ruleset is defined in `config/ruleset/`
- **WHEN** `terraform plan` is executed
- **THEN** no `github_organization_ruleset` resources are planned
- **AND** the `skipped_org_rulesets` output lists the skipped ruleset names

#### Scenario: Pro tier — org rulesets skipped

- **GIVEN** `subscription: pro` is configured
- **AND** at least one org ruleset is defined
- **WHEN** `terraform plan` is executed
- **THEN** no `github_organization_ruleset` resources are planned

#### Scenario: Team tier — org rulesets applied

- **GIVEN** `subscription: team` is configured
- **AND** at least one org ruleset is defined
- **WHEN** `terraform apply` is executed
- **THEN** `github_organization_ruleset` resources are created

#### Scenario: Enterprise tier — org rulesets applied

- **GIVEN** `subscription: enterprise` is configured
- **WHEN** `terraform apply` is executed
- **THEN** all org rulesets are created without restriction

---

## MODIFIED Requirements

### Requirement: Repository Rulesets (MODIFIED)

**Original:** The system SHALL support repository rulesets for branch protection and policy enforcement.

**Modification:** Repository rulesets are limited to definitions with `scope: repository` or no
`scope` field. Definitions with `scope: organization` are excluded from the repository-level
rulesets map and are not available for assignment via `rulesets:` in groups or repos.

#### Scenario: Org-scoped ruleset not assignable to repositories

- **GIVEN** `config/ruleset/org-rulesets.yml` defines a ruleset with `scope: organization`
- **AND** a repository config references this ruleset by name via `rulesets: ["org-main-protection"]`
- **WHEN** `terraform plan` is executed
- **THEN** the org-scoped ruleset is silently ignored (treated as a missing ruleset reference)
  OR an error is raised indicating org-scoped rulesets cannot be assigned per-repository

---

## MODIFIED Requirements

### Requirement: Subscription Tier Awareness (MODIFIED)

**Addition:** The system SHALL skip organization-level rulesets on `free` and `pro` plans, and
SHALL list skipped org rulesets in a dedicated warning output. The `team` and `enterprise` tiers
allow organization rulesets.

#### Scenario: Free tier org rulesets skipped with warning output

- **GIVEN** `subscription: free`
- **AND** org rulesets are defined
- **WHEN** `terraform apply` completes
- **THEN** the output `skipped_org_rulesets` contains the names of skipped org rulesets
