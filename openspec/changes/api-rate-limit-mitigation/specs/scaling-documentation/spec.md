## ADDED Requirements

### Requirement: Resource-per-repository API cost documentation

The module SHALL include documentation in `docs/` that lists the API calls made per repository during a Terraform plan refresh.

#### Scenario: Documentation includes resource breakdown table

- **WHEN** a user reads the scaling documentation
- **THEN** it SHALL contain a table showing each resource type (`github_repository`, `github_team_repository`, `github_repository_collaborator`, `github_repository_ruleset`, `github_actions_repository_permissions`, `github_repository_webhook`) and its cardinality per repository

### Requirement: Rate limit threshold documentation

The documentation SHALL include a table showing estimated API call counts for different organization sizes and which GitHub authentication limits they hit.

#### Scenario: Threshold table covers common org sizes

- **WHEN** a user reads the scaling documentation
- **THEN** it SHALL contain a table with rows for at least 100, 500, 1000, and 2000 repositories, showing estimated API calls and whether they fit within PAT (5,000/hr) and GitHub App (15,000/hr) limits

### Requirement: Provider tuning guidance

The documentation SHALL include recommended `read_delay_ms` and `write_delay_ms` values for different organization sizes.

#### Scenario: Tuning recommendations by org size

- **WHEN** a user reads the scaling documentation
- **THEN** it SHALL contain specific provider configuration examples for small (<100 repos), medium (100-500), and large (500+) organizations

### Requirement: Partitioning strategy documentation

The documentation SHALL explain the repository partitioning feature with examples of directory layout, variable usage, and CI integration.

#### Scenario: Documentation includes end-to-end partitioning example

- **WHEN** a user reads the scaling documentation
- **THEN** it SHALL contain a complete example showing directory layout, consumer module configuration with `repository_partitions`, and CI script usage with `detect-partitions.sh`

### Requirement: Documentation location

The scaling documentation SHALL be located in the `docs/` directory.

#### Scenario: Documentation file exists in docs/

- **WHEN** a user looks for scaling guidance
- **THEN** they SHALL find it at a file under `docs/` (e.g., `docs/scaling.md`)
