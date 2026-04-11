# partition-detection Specification

## Purpose

Define the requirements for the git-based partition detection script that identifies which
repository partitions are affected by changes in a git diff.

## Requirements

### Requirement: Git-based partition detection script

The module SHALL include a script at `scripts/detect-partitions.sh` that analyzes git diff output and outputs affected partition names.

#### Scenario: Script accepts git diff range

- **WHEN** the script is invoked as `./scripts/detect-partitions.sh main...HEAD`
- **THEN** it SHALL analyze changed files between the specified git refs

### Requirement: Shared config changes trigger all partitions

When files in shared configuration directories change, the script SHALL output ALL partition names because shared config can affect any repository.

#### Scenario: Group config changes

- **WHEN** `config/group/oss.yml` was modified in the git diff
- **THEN** the script SHALL output all partition directory names

#### Scenario: Ruleset config changes

- **WHEN** a file under `config/ruleset/` was modified in the git diff
- **THEN** the script SHALL output all partition directory names

#### Scenario: Webhook config changes

- **WHEN** a file under `config/webhook/` was modified in the git diff
- **THEN** the script SHALL output all partition directory names

#### Scenario: Top-level config.yml changes

- **WHEN** `config/config.yml` was modified in the git diff
- **THEN** the script SHALL output all partition directory names

### Requirement: Top-level repository file changes do not trigger partitions

Changes to top-level files in `config/repository/` SHALL NOT trigger partition plans because those files are always loaded regardless of partition selection.

#### Scenario: Only top-level repo files changed

- **WHEN** only `config/repository/common.yml` was modified in the git diff
- **THEN** the script SHALL output an empty list (no partitions needed)

### Requirement: Partition-specific changes trigger only affected partitions

Changes to files within partition subdirectories SHALL trigger only those specific partitions.

#### Scenario: Single partition changed

- **WHEN** only `config/repository/infra/ci-tooling.yml` was modified
- **THEN** the script SHALL output only `infra`

#### Scenario: Multiple partitions changed

- **WHEN** `config/repository/infra/ci.yml` and `config/repository/platform/billing.yml` were modified
- **THEN** the script SHALL output `infra` and `platform`

### Requirement: Terraform-friendly output format

The script SHALL support a `--tfvar` flag that formats output as a Terraform list literal.

#### Scenario: Default output format

- **WHEN** the script is invoked without `--tfvar`
- **THEN** output SHALL be one partition name per line

#### Scenario: Terraform variable format

- **WHEN** the script is invoked with `--tfvar`
- **THEN** output SHALL be a JSON array (e.g., `["infra", "platform"]`)

### Requirement: Combined changes follow escalation rules

When multiple types of changes are present in the same diff, the script SHALL follow escalation: shared config changes take precedence over partition-specific changes.

#### Scenario: Shared config plus partition-specific changes

- **WHEN** both `config/group/oss.yml` and `config/repository/infra/repos.yml` were modified
- **THEN** the script SHALL output all partition names (shared config change escalates)

#### Scenario: Top-level repo files plus partition-specific changes

- **WHEN** both `config/repository/common.yml` and `config/repository/infra/repos.yml` were modified
- **THEN** the script SHALL output only `infra` (top-level files do not escalate; they are always loaded)

### Requirement: No config changes detected

When no configuration files are changed in the diff range, the script SHALL signal that no Terraform run is needed.

#### Scenario: No config files in diff

- **WHEN** the git diff contains only non-config files (e.g., `README.md`, `scripts/validate.py`)
- **THEN** the script SHALL output an empty result and exit with code 0
