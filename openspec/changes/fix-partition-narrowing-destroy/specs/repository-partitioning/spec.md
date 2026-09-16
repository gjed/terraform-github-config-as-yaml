## MODIFIED Requirements

### Requirement: Partition selection via variable

The module SHALL accept a `repository_partitions` variable of type `list(string)` that specifies
which subdirectories to load. An empty list SHALL mean "load all partitions." Partition selection
is a **static state-sharding mechanism**: a non-empty value SHALL be paired with a dedicated
Terraform state (its own root module and backend) that manages only that partition's repositories,
set once and never varied between plans against that same state. Narrowing a non-empty selection
against a state that has ever managed repositories outside the new selection is unsupported and
plans their destruction, because Terraform has no mechanism to leave an orphaned `for_each`
instance untouched.

#### Scenario: Empty partitions list loads everything

- **WHEN** `repository_partitions = []` (default)
- **THEN** the module SHALL discover all subdirectories and load files from all of them, plus top-level files

#### Scenario: Specific partitions restrict loading

- **WHEN** `repository_partitions = ["infra", "platform"]`
- **THEN** the module SHALL load only files from `config/repository/infra/` and `config/repository/platform/`, plus top-level files
- **THEN** files in other subdirectories (e.g., `config/repository/legacy/`) SHALL NOT be loaded

#### Scenario: Specific partitions restrict loading in a dedicated state

- **WHEN** `repository_partitions = ["infra"]` is set in a root module whose state has only ever
  managed the `infra` partition
- **THEN** the module SHALL load only files from `config/repository/infra/`, plus top-level files
- **AND** no repository outside `infra` exists in that state to be destroyed

#### Scenario: Narrowing against a shared state is unsupported

- **WHEN** `repository_partitions` is changed from `[]` to `["infra"]` in a root module whose state
  already contains repositories from other partitions
- **THEN** Terraform plans to destroy every repository outside `infra`
- **AND** this is documented as unsupported usage, not a module defect to be silently prevented

## ADDED Requirements

### Requirement: Partition narrowing warning

The module SHALL emit a plan-time warning whenever `repository_partitions` selects a non-empty
strict subset of the partitions discovered under `config/repository/`, since this is the only
condition observable from within Terraform configuration that correlates with the destroy-on-
narrow risk. The warning SHALL NOT fail the plan, because a dedicated per-partition state
legitimately trips this condition on every run. This is in addition to, not a replacement for,
the existing partition name validation check.

#### Scenario: Strict subset triggers a warning

- **GIVEN** `config/repository/` contains partitions `infra`, `product`, and `legacy`
- **WHEN** `repository_partitions = ["infra"]`
- **THEN** `terraform plan` succeeds
- **AND** a warning is emitted referencing the state-sharding requirement

#### Scenario: Empty or full selection produces no warning

- **WHEN** `repository_partitions = []`, or `repository_partitions` lists all discovered partitions
- **THEN** no narrowing warning is emitted
