# repository-partitioning Specification

## Purpose

Define the requirements for subdirectory-based repository partitioning, allowing repository YAML
configurations to be organized into named partitions for selective loading.

## Requirements

### Requirement: Subdirectory-based repository partitioning

The module SHALL support organizing repository YAML configuration files into subdirectories under
`config/repository/`. Each subdirectory is a named partition. Only one level of nesting SHALL be
supported.

#### Scenario: Flat layout with no subdirectories (backward compatibility)

- **WHEN** `config/repository/` contains only `*.yml` files and no subdirectories
- **THEN** the module SHALL load all `*.yml` files, behaving identically to the current implementation

#### Scenario: Mixed layout with top-level files and subdirectories

- **WHEN** `config/repository/` contains both top-level `*.yml` files and subdirectories with `*.yml` files
- **THEN** the module SHALL load all top-level files and all files from all subdirectories when
  `repository_partitions` is empty

#### Scenario: Nested subdirectories are ignored

- **WHEN** `config/repository/infra/sub/file.yml` exists (two levels deep)
- **THEN** the module SHALL NOT load `file.yml` because only one level of nesting is supported

### Requirement: Top-level files always loaded

Top-level `*.yml` files directly under `config/repository/` SHALL always be loaded, regardless of
the `repository_partitions` variable value.

#### Scenario: Top-level files loaded even when partitions are filtered

- **WHEN** `repository_partitions = ["infra"]` and `config/repository/common.yml` exists
- **THEN** both `common.yml` and all files under `config/repository/infra/` SHALL be loaded

#### Scenario: Top-level files loaded when partitions list is empty

- **WHEN** `repository_partitions = []`
- **THEN** all top-level files and all subdirectory files SHALL be loaded

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
- **THEN** the module SHALL load only files from `config/repository/infra/` and
  `config/repository/platform/`, plus top-level files
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

### Requirement: Partition name validation

The module SHALL validate that all names in `repository_partitions` correspond to existing subdirectories under `config/repository/`.

#### Scenario: Valid partition names

- **WHEN** `repository_partitions = ["infra"]` and `config/repository/infra/` exists
- **THEN** validation SHALL pass

#### Scenario: Invalid partition name

- **WHEN** `repository_partitions = ["nonexistent"]` and no `config/repository/nonexistent/` directory exists
- **THEN** the module SHALL emit a warning identifying the invalid partition name

### Requirement: Duplicate detection across partitions

Existing duplicate key detection SHALL work across partition boundaries. A repository name defined
in multiple files across different partitions SHALL be detected as a duplicate.

#### Scenario: Same repo name in two partition files

- **WHEN** `config/repository/infra/repos.yml` defines repo `my-service` AND
  `config/repository/platform/repos.yml` also defines repo `my-service`
- **THEN** the duplicate detection logic SHALL identify this as a duplicate and include both file paths in the error

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
