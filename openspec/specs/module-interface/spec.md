# module-interface Specification

## Purpose

Define the public interface of the `terraform/` reusable module: the input variables consumers
must or may set, the provider contract (consumers configure their own), and the outputs the module
exposes. This spec does not cover internal YAML-parsing logic (see `repository-management`) or
the consumer-facing example setup (see `consumer-template`).

## Requirements

### Requirement: Config Path Variable

The module SHALL accept a `config_path` variable that consumers use to point the module at their YAML
configuration directory. The value MUST be a static string known at plan time (e.g.
`"${path.root}/config"`); computed values are not supported due to Terraform's `file()` evaluation
constraints.

#### Scenario: Consumer sets config_path

- **WHEN** a consumer calls the module with `config_path = "${path.root}/config"`
- **THEN** the module reads all YAML files from the consumer's `config/` directory
- **AND** the directory structure under that path matches the expected layout (`config.yml`,
  `group/*.yml`, `repository/*.yml`, `ruleset/*.yml`, `webhook/*.yml`, `membership/*.yml`)

#### Scenario: Static path required

- **WHEN** a consumer attempts to pass a computed value for `config_path`
- **THEN** Terraform fails at plan time with a path evaluation error
- **AND** the module documentation instructs consumers to use a static `"${path.root}/..."` path

______________________________________________________________________

### Requirement: Provider-Agnostic Module Root

The module SHALL NOT contain a `provider "github"` block. Consumers MUST configure the GitHub
provider in their own root module, including setting the `owner` field directly.

#### Scenario: Consumer configures provider

- **WHEN** a consumer's `main.tf` declares `provider "github" { owner = "my-org" }`
- **AND** calls the module
- **THEN** the module uses the inherited provider without conflict

#### Scenario: Module without provider block

- **WHEN** the module is called without any inline provider configuration
- **THEN** Terraform does not emit a provider-configuration warning
- **AND** the module inherits the provider from the caller

______________________________________________________________________

### Requirement: Webhook Secrets Variable

The module SHALL expose a `webhook_secrets` variable (sensitive map of strings) so consumers can
inject webhook secret values at runtime without hardcoding them in configuration files.

#### Scenario: Consumer provides webhook secret

- **WHEN** a consumer passes `webhook_secrets = { MY_SECRET = "abc123" }` # pragma: allowlist secret
- **AND** a webhook config references `env:MY_SECRET`
- **THEN** the module resolves the secret value at apply time

______________________________________________________________________

### Requirement: Membership Management Variable

The module SHALL accept a `membership_management_enabled` variable of type `bool` that defaults to
`false`. When set to `true`, the module manages organization membership from YAML files in the
`membership/` subdirectory of `config_path`.

#### Scenario: Consumer enables membership management

- **WHEN** a consumer calls the module with `membership_management_enabled = true`
- **THEN** the module reads membership YAML files from `config_path/membership/*.yml`
- **AND** manages organization membership resources accordingly

#### Scenario: Consumer does not set membership variable

- **WHEN** a consumer does not set `membership_management_enabled`
- **THEN** the variable defaults to `false`
- **AND** the module does not create or manage any membership resources

______________________________________________________________________

### Requirement: Repository Partitions Variable

The module SHALL accept a `repository_partitions` variable of type `list(string)` that defaults to
`[]`. This variable allows consumers to limit which repositories are managed in a given Terraform
run, mitigating GitHub API rate limits for large organizations.

#### Scenario: Default value preserves backward compatibility

- **WHEN** a consumer does not set `repository_partitions`
- **THEN** the variable defaults to `[]`
- **AND** the module manages all repositories defined in the configuration

#### Scenario: Consumer sets specific partitions

- **WHEN** a consumer passes `repository_partitions = ["a-m"]`
- **THEN** the module only manages repositories that match the specified partitions
- **AND** repositories outside the partitions are not included in the Terraform plan

#### Scenario: Variable is documented

- **WHEN** a consumer reads the module documentation
- **THEN** the `repository_partitions` variable is described with its type, default, and purpose

______________________________________________________________________

### Requirement: Module Outputs

The module SHALL expose the following outputs so consumers can reference managed resource details
without reading internal state directly:

- `repositories` — map of managed repositories with name, URL, SSH URL, and visibility
- `repository_count` — total number of managed repositories
- `organization` — GitHub organization name derived from `config.yml`
- `subscription_tier` — GitHub subscription tier derived from `config.yml`
- `subscription_warnings` — warnings about features skipped due to tier limitations
- `duplicate_key_warnings` — warnings about duplicate keys across split config files
- `managed_members` — map of managed organization members with username and role
- `managed_member_count` — total number of managed organization members
- `org_webhooks` — map of managed organization webhooks with URL and events

#### Scenario: Consumer reads organization output

- **WHEN** a consumer references `module.github_org.organization`
- **THEN** the value equals the `organization` field from `config/config.yml`

#### Scenario: Consumer reads repository URLs

- **WHEN** `terraform apply` completes
- **THEN** `module.github_org.repositories` contains an entry for each managed repo
- **AND** each entry includes `url`, `ssh_url`, and `visibility`

#### Scenario: Consumer reads membership output

- **WHEN** `terraform apply` completes with `membership_management_enabled = true`
- **THEN** `module.github_org.managed_members` contains an entry for each managed member
- **AND** each entry includes the username and role

#### Scenario: Membership output when disabled

- **WHEN** `membership_management_enabled` is `false` or unset
- **THEN** `module.github_org.managed_members` is an empty map
- **AND** `module.github_org.managed_member_count` is `0`

#### Scenario: Consumer reads org webhook output

- **WHEN** `terraform apply` completes with organization webhooks configured
- **THEN** `module.github_org.org_webhooks` contains an entry for each managed org webhook
- **AND** each entry includes the webhook URL and events

#### Scenario: Consumer reads org webhook output with no org webhooks

- **WHEN** no organization webhooks are configured
- **THEN** `module.github_org.org_webhooks` is an empty map
