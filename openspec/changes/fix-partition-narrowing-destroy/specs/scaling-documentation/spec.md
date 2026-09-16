## MODIFIED Requirements

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

## ADDED Requirements

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
