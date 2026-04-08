# Change: Add Webhook Configuration Support

Relates to: [Issue #4](https://github.com/gjed/github-as-yaml/issues/4)

## Why

Webhooks for CI/CD integrations, notifications, and external services must be configured manually today. This
leads to inconsistent webhook configurations across repositories, missing webhooks after repository creation,
and no version control for webhook settings. Managing webhooks as code follows the same GitOps pattern already
established for repository settings, teams, collaborators, and rulesets.

## What Changes

- **ADDED**: Webhook definitions in `config/webhook/` directory (follows split config pattern)
- **ADDED**: Webhook assignment by reference in groups and repositories
- **ADDED**: Support for inline webhook definitions in groups/repositories
- **ADDED**: Webhook inheritance from configuration groups with merge-by-name semantics
- **ADDED**: Secure secret handling via environment variable references (`env:VAR_NAME`)
- **ADDED**: Terraform `github_repository_webhook` resource management in the repository module

### Configuration Pattern

Webhooks are defined in `config/webhook/` and referenced by name:

```yaml
# config/webhook/ci.yml
jenkins-ci:
  url: https://jenkins.example.com/github-webhook/
  content_type: json
  secret: env:JENKINS_WEBHOOK_SECRET
  events: [push, pull_request]
  active: true

# config/group/with-ci.yml
with-ci:
  webhooks:
    - jenkins-ci          # Reference by name

# config/repository/my-repo.yml
my-repo:
  groups: [with-ci]
  webhooks:
    - slack-notify        # Additional webhook
    - name: custom        # Inline definition also supported
      url: https://custom.example.com
      events: [release]
```

### Webhook Schema

| Field          | Description                              | Required |
| -------------- | ---------------------------------------- | -------- |
| `url`          | Webhook endpoint URL                     | Yes      |
| `content_type` | `json` or `form` (default: `json`)       | No       |
| `secret`       | Webhook secret (`env:VAR_NAME` format)   | No       |
| `events`       | List of GitHub events to trigger         | Yes      |
| `active`       | Enable/disable webhook (default: `true`) | No       |
| `insecure_ssl` | Skip SSL verification (default: `false`) | No       |

### Merge Behavior

- Groups applied in order; later groups override earlier by webhook name
- Repository webhooks override group webhooks by name
- Webhooks with unique names are all included

### Terraform Resource

- `github_repository_webhook`

## Impact

- **Affected specs**: `repository-management`
- **Affected code**:
  - `terraform/modules/repository/main.tf` - Add webhook resource
  - `terraform/modules/repository/variables.tf` - Add webhooks variable
  - `terraform/yaml-config.tf` - Add webhook definitions loading and merging logic
  - `config/webhook/` - New directory for webhook definitions (examples)

## Out of Scope

- Organization-level webhooks (can be addressed in a separate change)
- Webhook delivery history or monitoring
- Automated webhook secret rotation
