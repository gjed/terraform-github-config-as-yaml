## ADDED Requirements

### Requirement: One-level subdirectory organization of repository files

The module SHALL load repository YAML files from top-level `*.yml` files directly under
`config/repository/` and from `*.yml` files in immediate subdirectories of `config/repository/`.
All discovered files SHALL always be loaded; subdirectories are purely organizational and carry no
selection semantics. Only one level of nesting SHALL be supported. Duplicate repository keys SHALL
be detected across all loaded files regardless of which directory defines them.

#### Scenario: Flat layout

- **WHEN** `config/repository/` contains only top-level `*.yml` files
- **THEN** the module SHALL load all of them

#### Scenario: Mixed layout is fully loaded

- **WHEN** `config/repository/` contains top-level `*.yml` files and subdirectories with `*.yml` files
- **THEN** the module SHALL load all top-level files and all files from all subdirectories

#### Scenario: Nested subdirectories are ignored

- **WHEN** `config/repository/infra/sub/file.yml` exists (two levels deep)
- **THEN** the module SHALL NOT load `file.yml`

#### Scenario: Duplicate keys across directories are detected

- **WHEN** `config/repository/infra/repos.yml` and `config/repository/platform/repos.yml` both define repo `my-service`
- **THEN** duplicate detection SHALL flag `my-service` and report both file paths
