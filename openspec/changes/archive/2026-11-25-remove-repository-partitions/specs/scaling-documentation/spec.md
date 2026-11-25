## MODIFIED Requirements

### Requirement: `-refresh=false` as primary scaling guidance

The documentation SHALL present `-refresh=false` on PR/merge plans, combined with a scheduled
full-refresh plan as the drift-detection authority, as the sole recommended way to reduce
`terraform plan` API cost. It SHALL state that this pattern requires no state migration and
carries no destroy risk, and SHALL recommend a GitHub App installation token for organizations
whose full-refresh plan approaches PAT rate limits.

#### Scenario: Documentation recommends -refresh=false first

- **WHEN** a user reads the scaling documentation's recommendations section
- **THEN** it SHALL describe the `-refresh=false` PR-plan and scheduled full-refresh pattern
- **AND** it SHALL state that this pattern requires no state migration and carries no destroy risk

## REMOVED Requirements

### Requirement: Partitioning strategy documentation

**Reason**: The repository partitioning feature is removed; there is no partitioning strategy to
document.
**Migration**: `docs/scaling.md` drops the Repository Partitioning and `detect-partitions.sh`
sections; `-refresh=false` plus GitHub App tokens is the documented scaling path.
