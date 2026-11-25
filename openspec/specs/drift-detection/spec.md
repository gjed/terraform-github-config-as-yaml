# drift-detection Specification

## Purpose
Detect when the real GitHub state differs from the Terraform configuration and report the difference in
a form that separates routine changes from critical and security-weakening ones, usable from any CI
system or a developer terminal.

## Requirements

### Requirement: Drift Check Exit Codes

The drift check command SHALL plan with a full refresh and exit with `0` when the plan contains no
resource changes, `2` when it contains resource changes, `3` when it would destroy or replace a
`github_repository`, and `1` on any error (missing tool, failed plan, unreadable or invalid plan JSON).
Whether the plan has changes SHALL be decided from the plan JSON, not the Terraform exit status alone.

#### Scenario: No drift

- **WHEN** every resource change in the plan is `no-op` or `read`
- **THEN** the command prints a no-drift report and exits `0`

#### Scenario: Drift

- **WHEN** the plan creates, updates, or deletes at least one resource and none is a destroyed or
  replaced repository
- **THEN** the command prints the report and exits `2`

#### Scenario: Repository destroy or replace

- **WHEN** the plan deletes or replaces a `github_repository`
- **THEN** the command reports it as critical and exits `3`

#### Scenario: Plan fails

- **WHEN** `terraform plan` or `terraform show` exits with an error
- **THEN** the command prints a clear error and exits `1` without a report

#### Scenario: Refresh is never skipped

- **WHEN** the command runs `terraform plan`
- **THEN** the plan is a full refresh, so out-of-band changes are visible

### Requirement: Drift Check Parameters

The drift check command SHALL accept its parameters as options, without requiring the caller to source
an environment file or prepare the shell. It SHALL support `--format text|markdown|json`,
`--plan-file PATH`, and `--repo NAME`. Progress messages SHALL go to stderr so that the report on stdout
is machine-readable.

#### Scenario: Single repository

- **WHEN** `--repo my-repo` is given
- **THEN** the plan is limited to that repository's module instance, as `make plan-repo` does

#### Scenario: Keep the plan file

- **WHEN** `--plan-file PATH` is given
- **THEN** the binary plan is written to `PATH` and kept after the command exits

#### Scenario: Temporary plan file

- **WHEN** `--plan-file` is not given
- **THEN** the plan is written to a temporary file that is removed when the command exits

#### Scenario: Invalid option

- **WHEN** an unknown option or an unsupported `--format` is given
- **THEN** the command prints usage and exits `1`

### Requirement: Change Categorisation

The report SHALL group resource changes by repository, with organization-level resources under their own
group, and classify each change as create, update, delete, or replace. Changes whose actions are only
`no-op` or `read` SHALL be ignored.

#### Scenario: Grouping by repository

- **WHEN** the plan changes resources of two repositories and one organization-level resource
- **THEN** the report lists three groups, each with its own changes

#### Scenario: Replace

- **WHEN** a resource's actions are `delete` and `create`
- **THEN** it is classified as replace

#### Scenario: Attribute diff

- **WHEN** a resource is updated
- **THEN** the report lists each changed attribute with its before and after value

### Requirement: Critical Change Flagging

The report SHALL flag as critical any destroy or replace of a `github_repository`, and any change that
would weaken security: a repository visibility change from private or internal to public, deletion or
disabling of a branch protection or ruleset, and removal of required signatures.

#### Scenario: Visibility becomes public

- **WHEN** a repository update changes visibility from `private` to `public`
- **THEN** the change is flagged critical with a reason naming the visibility change

#### Scenario: Protection deleted or disabled

- **WHEN** a branch protection or ruleset is deleted, or a ruleset's enforcement becomes `disabled`
- **THEN** the change is flagged critical

#### Scenario: Signatures no longer required

- **WHEN** a ruleset's `required_signatures` rule or a branch protection's `require_signed_commits`
  goes from enabled to disabled
- **THEN** the change is flagged critical

#### Scenario: Critical changes listed first

- **WHEN** the report contains critical changes
- **THEN** they are summarised in a dedicated section before the per-repository groups

### Requirement: Sensitive Value Masking

The report SHALL NOT print values that the plan marks as sensitive. Such attributes SHALL appear as
`(sensitive)` in every output format.

#### Scenario: Sensitive attribute changes

- **WHEN** an updated resource has a sensitive attribute
- **THEN** the report shows `(sensitive)` for that attribute and the plan's value appears nowhere in the
  output

### Requirement: Report Formats

The report helper SHALL render the same findings as coloured text on a TTY (plain text otherwise, and
when `NO_COLOR` is set), as markdown suitable for a pull request comment, and as JSON with a summary,
the critical findings, and the changes grouped by repository.

#### Scenario: Text format

- **WHEN** the format is `text` and stdout is not a TTY
- **THEN** the output has no ANSI escape sequences

#### Scenario: Markdown format

- **WHEN** the format is `markdown`
- **THEN** the output is a markdown document with a summary, a critical section when applicable, and one
  heading per group

#### Scenario: JSON format

- **WHEN** the format is `json`
- **THEN** the output is a single valid JSON document with a summary, critical findings, and grouped
  changes

### Requirement: Make Target

The repository SHALL provide `make drift-check` that runs the drift check on the module with the same
`TF_VAR_config_path` as the other targets, accepting optional `REPO` and `FORMAT` variables.

#### Scenario: Run through make

- **WHEN** a developer runs `make drift-check REPO=my-repo FORMAT=markdown`
- **THEN** the drift check runs for that repository and prints markdown

### Requirement: Drift Documentation

`AGENTS.md` and `README.md` SHALL document how to run the drift check, its exit codes, and what the
report flags as critical.

#### Scenario: Documentation present

- **WHEN** a user reads `AGENTS.md`
- **THEN** they find a "Detecting drift" section covering the command, exit codes, and output formats
