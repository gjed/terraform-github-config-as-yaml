## ADDED Requirements

### Requirement: Subdirectory-based repository partitioning

The module SHALL support organizing repository YAML configuration files into subdirectories under `config/repository/`. Each subdirectory is a named partition. Only one level of nesting SHALL be supported.

#### Scenario: Flat layout with no subdirectories (backward compatibility)

- **WHEN** `config/repository/` contains only `*.yml` files and no subdirectories
- **THEN** the module SHALL load all `*.yml` files, behaving identically to the current implementation

#### Scenario: Mixed layout with top-level files and subdirectories

- **WHEN** `config/repository/` contains both top-level `*.yml` files and subdirectories with `*.yml` files
- **THEN** the module SHALL load all top-level files and all files from all subdirectories when `repository_partitions` is empty

#### Scenario: Nested subdirectories are ignored

- **WHEN** `config/repository/infra/sub/file.yml` exists (two levels deep)
- **THEN** the module SHALL NOT load `file.yml` because only one level of nesting is supported

### Requirement: Top-level files always loaded

Top-level `*.yml` files directly under `config/repository/` SHALL always be loaded, regardless of the `repository_partitions` variable value.

#### Scenario: Top-level files loaded even when partitions are filtered

- **WHEN** `repository_partitions = ["infra"]` and `config/repository/common.yml` exists
- **THEN** both `common.yml` and all files under `config/repository/infra/` SHALL be loaded

#### Scenario: Top-level files loaded when partitions list is empty

- **WHEN** `repository_partitions = []`
- **THEN** all top-level files and all subdirectory files SHALL be loaded

### Requirement: Partition selection via variable

The module SHALL accept a `repository_partitions` variable of type `list(string)` that specifies which subdirectories to load. An empty list SHALL mean "load all partitions."

#### Scenario: Empty partitions list loads everything

- **WHEN** `repository_partitions = []` (default)
- **THEN** the module SHALL discover all subdirectories and load files from all of them, plus top-level files

#### Scenario: Specific partitions restrict loading

- **WHEN** `repository_partitions = ["infra", "platform"]`
- **THEN** the module SHALL load only files from `config/repository/infra/` and `config/repository/platform/`, plus top-level files
- **THEN** files in other subdirectories (e.g., `config/repository/legacy/`) SHALL NOT be loaded

### Requirement: Partition name validation

The module SHALL validate that all names in `repository_partitions` correspond to existing subdirectories under `config/repository/`.

#### Scenario: Valid partition names

- **WHEN** `repository_partitions = ["infra"]` and `config/repository/infra/` exists
- **THEN** validation SHALL pass

#### Scenario: Invalid partition name

- **WHEN** `repository_partitions = ["nonexistent"]` and no `config/repository/nonexistent/` directory exists
- **THEN** the module SHALL emit a warning identifying the invalid partition name

### Requirement: Duplicate detection across partitions

Existing duplicate key detection SHALL work across partition boundaries. A repository name defined in multiple files across different partitions SHALL be detected as a duplicate.

#### Scenario: Same repo name in two partition files

- **WHEN** `config/repository/infra/repos.yml` defines repo `my-service` AND `config/repository/platform/repos.yml` also defines repo `my-service`
- **THEN** the duplicate detection logic SHALL identify this as a duplicate and include both file paths in the error
