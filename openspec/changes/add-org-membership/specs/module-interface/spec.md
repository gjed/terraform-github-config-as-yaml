# module-interface Specification (Delta)

## MODIFIED Requirements

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

#### Scenario: Consumer reads organization output

- **WHEN** a consumer references `module.github_org.organization`
- **THEN** the value equals the `organization` field from `config/config.yml`

#### Scenario: Consumer reads repository URLs

- **WHEN** `terraform apply` completes
- **THEN** `module.github_org.repositories` contains an entry for each managed repo
- **AND** each entry includes `url`, `ssh_url`, and `visibility`

#### Scenario: Consumer reads membership output

- **WHEN** `membership_management_enabled` is `true`
- **AND** `terraform apply` completes
- **THEN** `module.github_org.managed_members` contains an entry for each managed member
- **AND** each entry includes `username` and `role`

#### Scenario: Membership output when disabled

- **WHEN** `membership_management_enabled` is `false`
- **THEN** `module.github_org.managed_members` is an empty map
- **AND** `module.github_org.managed_member_count` is `0`

## ADDED Requirements

### Requirement: Membership Management Variable

The module SHALL accept a `membership_management_enabled` boolean variable that controls whether
organization membership resources are created. The variable SHALL default to `false`.

#### Scenario: Consumer enables membership management

- **WHEN** a consumer calls the module with `membership_management_enabled = true`
- **THEN** the module creates `github_membership` resources for entries in `config/membership/`

#### Scenario: Consumer does not set membership variable

- **WHEN** a consumer calls the module without setting `membership_management_enabled`
- **THEN** no `github_membership` resources are created
- **AND** the default value is `false`
