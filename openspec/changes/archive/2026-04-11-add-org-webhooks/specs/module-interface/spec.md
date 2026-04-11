## MODIFIED Requirements

### Requirement: Module Outputs

The module SHALL expose an additional output for organization webhook information.

#### Scenario: Consumer reads org webhook output

- **WHEN** `terraform apply` completes with org webhooks configured
- **THEN** `org_webhooks` output contains a map of webhook names to their URLs

#### Scenario: Consumer reads org webhook output with no org webhooks

- **WHEN** `terraform apply` completes without org webhooks configured
- **THEN** `org_webhooks` output is an empty map
