# consumer-template Specification

## Purpose

Define the requirements for the consumer-facing scaffolding bundled with the module: the
`examples/consumer/` directory, documentation (README and wiki), onboarding/offboarding script
support for module-wrapped state paths, and the initial release tag. This spec covers what the
repository provides to help adopters get started, not the module's internal Terraform logic.

## Requirements

### Requirement: Consumer Example Directory

The repository SHALL include an `examples/consumer/` directory that demonstrates the minimal
setup required to consume the module. The example MUST contain:

- A `main.tf` (≤ 20 lines) with `terraform` block, `provider "github"` block, and a single
  `module "github_org"` call with `config_path = "${path.root}/config"`.
- Stub config files (`config/config.yml`, `config/group/`, `config/repository/`, `config/ruleset/`)
  with inline comments explaining each field.
- A `README.md` describing how to copy and adapt the example.

#### Scenario: New user bootstraps a consumer repo

- **WHEN** a user copies `examples/consumer/` as the starting point for their org repo
- **THEN** they have a working Terraform setup that calls the module
- **AND** they only need to fill in their org name and add repository entries to the YAML stubs

#### Scenario: Consumer main.tf is minimal

- **WHEN** a user reads `examples/consumer/main.tf`
- **THEN** the file is no longer than 20 lines
- **AND** it contains exactly one `module` block calling this module
- **AND** it contains exactly one `provider "github"` block

______________________________________________________________________

### Requirement: Script Support for Nested Module State Paths

The `onboard-repos.sh` and `offboard-repos.sh` scripts SHALL accept a `--module-path` option that
prepends a module namespace to Terraform state resource addresses. When consumers wrap the module
in `module "github_org"`, state paths become
`module.github_org.module.repositories["<repo>"]` instead of `module.repositories["<repo>"]`.

#### Scenario: Consumer uses wrapped module state path

- **WHEN** `onboard-repos.sh --import --module-path module.github_org repo-name` is executed
- **THEN** the script imports to `module.github_org.module.repositories["repo-name"]`

#### Scenario: Direct layout (no --module-path)

- **WHEN** `onboard-repos.sh --import repo-name` is executed without `--module-path`
- **THEN** the script imports to `module.repositories["repo-name"]` (legacy direct layout)

______________________________________________________________________

### Requirement: Module README

The repository SHALL include a `README.md` (or update the existing one) with a dedicated section
documenting the module interface for consumers, including:

- All input variables with types, defaults, and descriptions.
- All outputs with descriptions.
- A complete consumer `main.tf` example.
- A note on the `config_path` static-string constraint.
- A migration guide for existing forks upgrading to the module pattern.

#### Scenario: Consumer evaluates the module

- **WHEN** a consumer reads the `README.md`
- **THEN** they can identify all required and optional variables
- **AND** they can see a copy-pasteable `main.tf` example
- **AND** they understand the `config_path` static-string constraint before configuring

#### Scenario: Existing fork migrates

- **WHEN** an existing fork maintainer reads the migration section of the README
- **THEN** they have step-by-step instructions for moving from the monolith layout to the
  consumer-module layout
- **AND** they know how to perform the required `terraform state mv` operations

______________________________________________________________________

### Requirement: Initial Module Release Tag

The repository SHALL have a git tag (`v1.0.0`) marking the first published version of the
standalone module so consumers can pin to a stable reference.

#### Scenario: Consumer pins to a release

- **WHEN** a consumer sets `source = "git::https://github.com/gjed/github-as-yaml.git?ref=v1.0.0"`
- **THEN** they receive the stable v1.0.0 module interface
- **AND** future changes to the module do not affect them until they update the `ref`
