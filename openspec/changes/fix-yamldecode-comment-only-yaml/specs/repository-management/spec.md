## ADDED Requirements

### Requirement: Comment-Only Configuration Files

The system SHALL treat a YAML configuration file that contains only comments and/or blank lines
as contributing no configuration, rather than failing to parse.

This applies to every split configuration directory: `<config_path>/repository/`,
`<config_path>/group/`, `<config_path>/ruleset/`, `<config_path>/membership/`, and
`<config_path>/branch-protection/`.

`<config_path>/config.yml` is exempt. It is required and must define `organization`, so an empty
document there is a configuration error regardless.

Detection SHALL strip whole-line comments and blank lines only. A `#` appearing inside a quoted
value SHALL NOT be treated as a comment, and such a file SHALL be decoded normally.

A file that contains any YAML content SHALL still be passed to `yamldecode()`, so malformed YAML
continues to fail at plan time with its original parse error. The system SHALL NOT suppress
parse errors by wrapping the decode in `try()`.

#### Scenario: Comment-only file in a configuration directory

- **GIVEN** `<config_path>/membership/` contains a file consisting only of comment lines
- **WHEN** Terraform is initialized and planned
- **THEN** the plan succeeds
- **AND** the file contributes no entries to the merged membership configuration

#### Scenario: Empty file in a configuration directory

- **GIVEN** `<config_path>/repository/` contains a zero-byte `.yml` file
- **WHEN** Terraform is initialized and planned
- **THEN** the plan succeeds
- **AND** the file contributes no entries to the merged repository configuration

#### Scenario: Comment-only file alongside real configuration

- **GIVEN** `<config_path>/repository/` contains `a-real.yml` defining `real-repo`
- **AND** the same directory contains `z-commented.yml` consisting only of comments
- **WHEN** Terraform is initialized and planned
- **THEN** the merged repository configuration contains exactly `real-repo`

#### Scenario: Malformed YAML still fails

- **GIVEN** a configuration file contains syntactically invalid YAML
- **WHEN** Terraform is initialized and planned
- **THEN** the plan fails with the underlying `yamldecode` parse error
- **AND** the error names the file and the line at which parsing failed

#### Scenario: Hash inside a quoted value is not a comment

- **GIVEN** a repository configuration contains `description: "value # not a comment"`
- **WHEN** Terraform is initialized and planned
- **THEN** the file is decoded normally
- **AND** the description retains the literal text `value # not a comment`
