# scaling-documentation Specification

## Purpose

Define the requirements for scaling documentation that covers API rate limits, resource costs per
repository, and partitioning strategy guidance.

## Requirements

### Requirement: Resource-per-repository API cost documentation

The module SHALL include documentation in `docs/` that lists the API calls made per repository during a Terraform plan refresh.

#### Scenario: Documentation includes resource breakdown table

- **WHEN** a user reads the scaling documentation
- **THEN** it SHALL contain a table showing each resource type (`github_repository`,
  `github_team_repository`, `github_repository_collaborator`, `github_repository_ruleset`,
  `github_actions_repository_permissions`, `github_repository_webhook`) and its cardinality per
  repository

### Requirement: Rate limit threshold documentation

The documentation SHALL include a table showing estimated API call counts for different
organization sizes and which GitHub authentication limits they hit.

#### Scenario: Threshold table covers common org sizes

- **WHEN** a user reads the scaling documentation
- **THEN** it SHALL contain a table with rows for at least 100, 500, 1000, and 2000 repositories,
  showing estimated API calls and whether they fit within PAT (5,000/hr) and GitHub App
  (15,000/hr) limits

### Requirement: Provider tuning guidance

The documentation SHALL include recommended `read_delay_ms` and `write_delay_ms` values for different organization sizes.

#### Scenario: Tuning recommendations by org size

- **WHEN** a user reads the scaling documentation
- **THEN** it SHALL contain specific provider configuration examples for small (\<100 repos),
  medium (100-500), and large (500+) organizations

### Requirement: Partitioning strategy documentation

The documentation SHALL explain the repository partitioning feature with examples of directory
layout, variable usage, and CI integration, framed as a **static state-sharding** mechanism. The
documentation SHALL NOT present a single-state example that computes `repository_partitions`
dynamically from a git diff and feeds it into a `terraform plan` against a shared state.

#### Scenario: Documentation includes end-to-end partitioning example

- **WHEN** a user reads the scaling documentation
- **THEN** it SHALL contain a complete example showing directory layout, a per-partition root
  module with its own backend configuration, and CI usage of `detect-partitions.sh` to select
  which per-partition job to run

#### Scenario: Destroy-risk warning names the actual safe path

- **WHEN** a user reads the partitioning warning about destroy-on-narrow risk
- **THEN** it SHALL point to the dedicated-per-partition-state requirement as the safe path
- **AND** it SHALL NOT claim that deletion protection (#37 / `archive_on_destroy`) makes narrowing
  against a shared state safe

### Requirement: Documentation location

The scaling documentation SHALL be located in the `docs/` directory.

#### Scenario: Documentation file exists in docs/

- **WHEN** a user looks for scaling guidance
- **THEN** they SHALL find it at a file under `docs/` (e.g., `docs/scaling.md`)

### Requirement: `-refresh=false` as primary scaling guidance

The documentation SHALL present `-refresh=false` on PR/merge plans, combined with a scheduled
full-refresh plan as the drift-detection authority, as the primary recommended way to reduce
`terraform plan` API cost for a single shared state — ahead of repository partitioning, which
SHALL be documented as the secondary option for organizations where a single state's full-refresh
plan itself exceeds API rate limits (roughly 2,000+ repositories).

#### Scenario: Documentation recommends -refresh=false first

- **WHEN** a user reads the scaling documentation's recommendations section
- **THEN** it SHALL describe the `-refresh=false` PR-plan and scheduled full-refresh pattern before
  describing repository partitioning
- **AND** it SHALL state that this pattern requires no state migration and carries no destroy risk
