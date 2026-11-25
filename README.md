# GitHub As YAML

Manage your GitHub organization's repositories as code using Terraform and YAML configuration.

<!-- markdownlint-disable MD033 -->

<p align="center">
  <img src="docs/logo.png" alt="GitHub As YAML" width="400">
</p>
<!-- markdownlint-enable MD033 -->

## Usage

```hcl
module "github_org" {
  source  = "gjed/config-as-yaml/github"
  version = "~> 1.0"

  config_path = "${path.root}/config"
}
```

Consumers must configure the GitHub provider in their own root module:

```hcl
provider "github" {
  owner = "your-org-name"
}
```

See the [consumer example](examples/consumer/) for a complete setup and the
[Wiki](https://github.com/gjed/terraform-github-config-as-yaml/wiki) for full
documentation.

## Features

- **YAML-based configuration** - Human-readable repository definitions
- **Configuration groups** - Share settings across multiple repositories (DRY)
- **Repository rulesets** - Enforce branch protection and policies
- **GitHub Actions permissions** - Control which actions can run and workflow permissions
- **Webhook management** - Configure CI/CD and notification webhooks as code
- **Secrets and variables** - Actions and Dependabot secrets and Actions variables, org and repo level
- **Environments** - Deployment branch policies, reviewers, wait timers, and environment secrets and variables
- **Subscription-aware** - Gracefully handles GitHub Free tier limitations
- **Onboarding script** - Easily import existing repositories
- **Drift detection** - Spot differences between GitHub and the configuration with `make drift-check`

## Requirements

| Name            | Version |
| --------------- | ------- |
| Terraform       | >= 1.0  |
| github provider | >= 6.12.0 |

A GitHub Personal Access Token with `repo` and `admin:org` scopes is required.

## Inputs

| Name              | Description                                                                                                                                                                                                | Type          | Default | Required |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | ------- | -------- |
| `config_path`     | Absolute path to the directory containing `config.yml`, `group/`, `repository/`, `ruleset/`, and `webhook/` subdirectories. Consumers should set this to `"${path.root}/config"`. Must be a static string. | `string`      | n/a     | yes      |
| `webhook_secrets` | Map of webhook secret names to their values. Keys should match the `VAR_NAME` in `env:VAR_NAME` patterns used in webhook configurations.                                                                   | `map(string)` | `{}`    | no       |
| `secret_values`   | Map of Actions and Dependabot secret names to their values. Keys must match the `VAR_NAME` in `env:VAR_NAME` references used in `config/secret/` and group/repository `secrets:` definitions.              | `map(string)` | `{}`    | no       |

## Outputs

| Name                     | Description                                                           |
| ------------------------ | --------------------------------------------------------------------- |
| `repositories`           | Map of managed repositories with their URLs, SSH URLs, and visibility |
| `repository_count`       | Total number of managed repositories                                  |
| `organization`           | GitHub organization being managed                                     |
| `subscription_tier`      | GitHub subscription tier                                              |
| `subscription_warnings`  | Warnings about features unavailable on current subscription tier      |
| `duplicate_key_warnings` | Warnings about duplicate keys in config files                         |
| `skipped_environments`   | Repositories whose environments were skipped by subscription tier     |

## Configuration Structure

The `config_path` directory should contain:

```text
config/
├── config.yml              # Organization name, subscription tier, global settings
├── group/                  # Configuration groups (one or more YAML files)
│   ├── base.yml
│   └── oss.yml
├── repository/             # Repository definitions (one or more YAML files)
│   └── repositories.yml
├── ruleset/                # Ruleset definitions (one or more YAML files)
│   └── rulesets.yml
├── secret/                 # Org Actions/Dependabot secrets and variables (optional, one or more YAML files)
│   └── secrets.yml
└── webhook/                # Webhook definitions (optional, one or more YAML files)
    └── webhooks.yml
```

### Example Configuration

```yaml
# config/repository/repositories.yml
terraform-modules:
  description: "Shared Terraform modules"
  groups: ["base", "oss"]
  topics: ["terraform"]

api-gateway:
  description: "Internal API gateway"
  groups: ["base", "internal"]
```

### Environments

Repository environments are defined under `environments:` in a group or repository. Groups apply in
order, and a repository entry replaces a group entry with the same environment name as a whole.

```yaml
# config/repository/repositories.yml
api-gateway:
  description: "Internal API gateway"
  groups: ["base", "internal"]
  environments:
    production:
      wait_timer: 10
      prevent_self_review: true
      reviewers:
        users: ["octocat"]
        teams: ["platform"]
      deployment_branch_policy:
        custom_branch_policies: true # or protected_branches: true, never both
        branch_patterns: ["main", "release/*"]
        tag_patterns: ["v*"]
      secrets:
        DEPLOY_TOKEN:
          value: "env:DEPLOY_TOKEN" # resolved from the secret_values input
      variables:
        REGION:
          value: "eu-west-1"
```

Environments, reviewers, wait timers, and deployment branch policies on private repositories need a
paid GitHub plan. On the `free` tier the environments of private repositories are skipped and listed
in the `skipped_environments` output. The names of managed environments, secrets, and variables are
exposed by the `repository_environments` output, never their values.

## Detecting Drift

`make drift-check` plans with a full refresh and reports where GitHub differs from the configuration,
grouped by repository, with destroyed repositories and security-weakening changes flagged as critical. The
plan also lists configuration changes that are merged but not yet applied, so run it against applied
configuration for a drift-only signal:

```bash
make drift-check                     # text report
make drift-check FORMAT=markdown     # markdown (also: json)
make drift-check REPO=my-repo        # one repository
```

`scripts/detect-drift.sh` exits `0` for no drift, `2` for drift, `3` when a repository would be destroyed or
replaced and `1` on error, so any CI system can schedule it. `make drift-check` prints the same report, but
GNU make turns every failing recipe into exit status 2, so CI that needs these codes must call the script
directly (after `export TF_VAR_config_path="$PWD/config"`). See `scripts/detect-drift.sh --help` and the
"Detecting drift" section of `AGENTS.md`.

## CI/CD Examples

[`ci/`](ci/README.md) holds copy-ready pipelines for GitHub Actions and Jenkins: a plan posted on every
pull request, an apply behind an approval gate that refuses to destroy a repository, and a nightly drift
check built on `scripts/detect-drift.sh`. It also has `backend.tf` examples (S3, GCS, Azure, Terraform
Cloud) and a [guide to the GitHub App credential](ci/docs/authentication.md) they need. The templates are
not run on this repository.

## GitHub Subscription Tiers

| Feature               | Free | Pro | Team | Enterprise |
| --------------------- | ---- | --- | ---- | ---------- |
| Public repo rulesets  | Yes  | Yes | Yes  | Yes        |
| Private repo rulesets | No   | Yes | Yes  | Yes        |
| Push rulesets         | No   | No  | Yes  | Yes        |
| Actions permissions   | Yes  | Yes | Yes  | Yes        |

Unsupported features are automatically skipped based on your subscription tier.

## Using as a Template (Forking)

This repository can also be used directly as a template. See the
[Quick Start Guide](https://github.com/gjed/terraform-github-config-as-yaml/wiki/Quick-Start)
for fork-based setup instructions.

### Commands (for forked usage)

```bash
make init      # Initialize Terraform
make plan      # Preview changes
make apply     # Apply changes
make validate  # Validate configuration
```

## Documentation

- [Quick Start Guide](https://github.com/gjed/terraform-github-config-as-yaml/wiki/Quick-Start) - Get up and running
- [Configuration Reference](https://github.com/gjed/terraform-github-config-as-yaml/wiki/Configuration-Reference) -
  All available options
- [Using as a Module](https://github.com/gjed/terraform-github-config-as-yaml/wiki/Using-as-a-Module) -
  Reusable module setup and migration guide
- [Customization Guide](https://github.com/gjed/terraform-github-config-as-yaml/wiki/Customization) - Extend the template
- [Examples](https://github.com/gjed/terraform-github-config-as-yaml/wiki/Examples) - Common configuration patterns
- [Troubleshooting](https://github.com/gjed/terraform-github-config-as-yaml/wiki/Troubleshooting) - Common issues and solutions

## License

[Apache 2.0](LICENSE)
