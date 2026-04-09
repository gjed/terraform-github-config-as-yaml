## ADDED Requirements

### Requirement: Organization Webhook Configuration

The system SHALL support organization-level webhook configuration by referencing webhook names
defined in `config/webhook/` from the `org_webhooks` list in `config/config.yml`. Organization
webhooks fire for events across all repositories in the organization.

#### Scenario: Define org webhooks by name reference

- **GIVEN** a webhook `audit-logger` is defined in `config/webhook/audit.yml`:
  ```yaml
  audit-logger:
    url: https://audit.example.com/github
    content_type: json
    secret: env:ORG_WEBHOOK_SECRET
    events:
      - repository
      - member
      - team
      - organization
    active: true
  ```
- **AND** `config/config.yml` contains:
  ```yaml
  org_webhooks:
    - audit-logger
  ```
- **WHEN** `terraform apply` is executed
- **THEN** a `github_organization_webhook` resource is created
- **AND** the webhook URL is `https://audit.example.com/github`
- **AND** the webhook triggers on repository, member, team, and organization events

#### Scenario: Multiple org webhooks

- **GIVEN** `config/config.yml` defines:
  ```yaml
  org_webhooks:
    - audit-logger
    - ci-notifier
  ```
- **AND** both `audit-logger` and `ci-notifier` are defined in `config/webhook/`
- **WHEN** `terraform apply` is executed
- **THEN** two `github_organization_webhook` resources are created
- **AND** each uses the settings from its respective webhook definition

#### Scenario: Org webhook with secret resolution

- **GIVEN** a webhook defines `secret: env:ORG_WEBHOOK_SECRET`
- **AND** `var.webhook_secrets` contains `{ ORG_WEBHOOK_SECRET = "supersecret" }`
- **WHEN** `terraform apply` is executed
- **THEN** the org webhook is created with the resolved secret value
- **AND** the secret is marked as sensitive in Terraform state

#### Scenario: Org webhook without secret

- **GIVEN** a webhook is defined without a `secret` field
- **AND** the webhook is referenced in `org_webhooks`
- **WHEN** `terraform apply` is executed
- **THEN** the org webhook is created without a secret

#### Scenario: Org webhook default values

- **GIVEN** an org webhook is defined with only required fields:
  ```yaml
  minimal-webhook:
    url: https://example.com/hook
    events:
      - push
  ```
- **WHEN** `terraform apply` is executed
- **THEN** the webhook uses `content_type: json` by default
- **AND** the webhook is active by default
- **AND** SSL verification is enabled by default

#### Scenario: No org webhooks configured

- **GIVEN** `config/config.yml` does not contain an `org_webhooks` key
- **WHEN** `terraform apply` is executed
- **THEN** no `github_organization_webhook` resources are created

#### Scenario: Empty org webhooks list

- **GIVEN** `config/config.yml` contains `org_webhooks: []`
- **WHEN** `terraform apply` is executed
- **THEN** no `github_organization_webhook` resources are created

#### Scenario: Reference undefined webhook in org_webhooks

- **GIVEN** `config/config.yml` references `org_webhooks: ["nonexistent-webhook"]`
- **AND** no webhook named `nonexistent-webhook` is defined in `config/webhook/`
- **WHEN** `terraform plan` is executed
- **THEN** Terraform fails with an error indicating the webhook is not defined

#### Scenario: Personal account skips org webhooks

- **GIVEN** `config/config.yml` contains `is_organization: false`
- **AND** `org_webhooks` is configured with valid webhook references
- **WHEN** `terraform apply` is executed
- **THEN** no `github_organization_webhook` resources are created

______________________________________________________________________

### Requirement: Organization Webhook Resource Management

The system SHALL create, update, and delete `github_organization_webhook` resources based on the
resolved org webhook configuration.

#### Scenario: Create org webhook

- **GIVEN** an org webhook is configured and does not exist in GitHub
- **WHEN** `terraform apply` is executed
- **THEN** the `github_organization_webhook` resource is created
- **AND** the configuration block includes url, content_type, secret, and insecure_ssl
- **AND** the events list is applied
- **AND** the active flag is applied

#### Scenario: Update org webhook

- **GIVEN** an existing org webhook's URL is changed in `config/webhook/`
- **WHEN** `terraform apply` is executed
- **THEN** the `github_organization_webhook` resource is updated with the new URL

#### Scenario: Remove org webhook

- **GIVEN** an org webhook name is removed from the `org_webhooks` list in `config/config.yml`
- **WHEN** `terraform apply` is executed
- **THEN** the corresponding `github_organization_webhook` resource is destroyed

#### Scenario: Shared webhook definition update

- **GIVEN** a webhook definition in `config/webhook/` is referenced by both a repository and
  `org_webhooks`
- **AND** the URL is changed in the webhook definition
- **WHEN** `terraform apply` is executed
- **THEN** both the repository webhook and the organization webhook are updated

## MODIFIED Requirements

### Requirement: YAML-Based Repository Configuration

The system SHALL read repository configurations from YAML files under the directory specified by
`var.config_path` using Terraform's native `yamldecode()` function. Additionally, the system SHALL
read the `org_webhooks` list from `config/config.yml` to resolve organization-level webhook
references.

#### Scenario: Load org webhooks from config.yml

- **WHEN** Terraform is initialized and planned
- **THEN** the system reads the `org_webhooks` list from `config/config.yml`
- **AND** defaults to an empty list if the key is absent
