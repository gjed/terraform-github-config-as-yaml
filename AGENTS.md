______________________________________________________________________

## Agents

This file provides guidance to AI coding agents working on this repository.

## Project Overview

This is a Terraform project for managing GitHub organization repositories using Infrastructure as Code.
Configuration is defined in YAML files in the `config/` directory and read directly by Terraform.

## Project Structure

```text
terraform-github-config-as-yaml/
├── main.tf                           # Terraform module entry point
├── variables.tf                      # Module input variables
├── outputs.tf                        # Module outputs
├── yaml-config.tf                    # YAML parsing and processing logic
├── modules/repository/               # Repository resource submodule
├── config/                           # Template YAML configuration files
│   ├── config.yml                    # Organization and global settings
│   ├── group/                        # Configuration groups (oss, internal, etc.)
│   ├── repository/                   # Repository definitions
│   ├── ruleset/                      # Ruleset definitions
│   └── membership/                   # Organization membership definitions (optional)
├── examples/consumer/                # Consumer example for module usage
├── scripts/
│   ├── validate-config.py            # Validates configuration files
│   ├── onboard-repos.sh              # Import existing repositories
│   ├── offboard-repos.sh             # Remove repos from management
│   └── migrate-state.sh              # State migration helper
└── .pre-commit-config.yaml           # Pre-commit hooks configuration
```

## Key Files

- `config/config.yml` - Organization name, subscription tier, and global defaults
- `config/groups.yml` - Configuration groups (oss, internal, etc.)
- `config/repositories.yml` - Repository definitions
- `config/rulesets.yml` - Ruleset definitions
- `main.tf` - Terraform entry point, sets GitHub organization
- `yaml-config.tf` - YAML parsing and processing logic
- `modules/repository/` - Repository resource module

## Common Tasks

### Adding a new repository

1. Edit `config/repositories.yml`
1. Add entry with description and groups
1. Assign appropriate groups (e.g., `["gjed", "internal"]` or `["gjed", "oss"]`)
1. Run `terraform plan` to preview, then `terraform apply`

### Modifying configuration groups

Edit `config/groups.yml`. Groups are merged when multiple are assigned to a repo.

### Creating and managing rulesets

Rulesets allow you to enforce branch protection and other repository rules across multiple repositories based on their groups.

There are two types of rulesets:

- **Repository rulesets** (`scope: repository` or no `scope`) — applied per-repository, assigned
  via `rulesets:` in groups or repositories.
- **Organization rulesets** (`scope: organization`) — applied at the org level across multiple
  repositories by `repository_name` pattern conditions. NOT assignable per-repo or per-group.

#### Repository rulesets

1. Edit a file in `config/ruleset/` to define a ruleset (no `scope` or `scope: repository`)
1. Each ruleset must specify:
   - `target`: Type of target (e.g., `branch`, `tag`)
   - `enforcement`: Enforcement level (`active`, `evaluate`, or `disabled`)
   - `conditions`: Conditions for when the ruleset applies (e.g., branch name patterns)
   - `rules`: Array of rules to enforce
1. Reference rulesets in groups or repositories by adding a `rulesets:` field

Example in `config/ruleset/default-rulesets.yml`:

```yaml
oss-main-protection:
  target: branch
  enforcement: active
  conditions:
    ref_name:
      include:
        - "~DEFAULT_BRANCH"
      exclude: []
  rules:
    - type: deletion
    - type: non_fast_forward
    - type: required_linear_history
    - type: pull_request
      parameters:
        required_approving_review_count: 1
        dismiss_stale_reviews_on_push: true
```

Example in `config/groups.yml`:

```yaml
oss:
  visibility: public
  # ... other settings
  rulesets:
    - oss-main-protection
```

Example for individual repo in `config/repositories.yml`:

```yaml
my-special-repo:
  description: "Special repo"
  groups: ["oss"]
  rulesets:
    - oss-main-protection
    - custom-ruleset
```

#### Organization rulesets

Organization rulesets apply rules globally across repositories, filtered by `repository_name`
conditions. They are defined in `config/ruleset/` with `scope: organization` and are NOT
referenced via `rulesets:` in groups or repositories.

Requires `team` or `enterprise` subscription. On `free`/`pro` plans, org rulesets are skipped
with a warning in the `skipped_org_rulesets` output.

Example in `config/ruleset/org-rulesets.yml`:

```yaml
org-main-protection:
  scope: organization          # Required: marks this as an org-level ruleset
  target: branch
  enforcement: active
  conditions:
    ref_name:
      include:
        - "~DEFAULT_BRANCH"
      exclude: []
    repository_name:           # Optional: which repos this applies to (default: all)
      include:
        - "*"
      exclude:
        - "sandbox-*"
  rules:
    - type: deletion
    - type: non_fast_forward
    - type: pull_request
      parameters:
        required_approving_review_count: 1
        dismiss_stale_reviews_on_push: true
```

Supported rule types:

- `deletion` - Prevent branch deletion
- `non_fast_forward` - Prevent force pushes
- `required_linear_history` - Require linear history
- `required_signatures` - Require signed commits
- `pull_request` - Require pull request reviews
- `required_status_checks` - Require status checks to pass
- `creation` - Control branch creation
- `update` - Control branch updates
- `required_deployments` - Require successful deployments (repository rulesets only)
- `branch_name_pattern` - Enforce branch naming patterns
- `commit_message_pattern` - Enforce commit message patterns
- `commit_author_email_pattern` - Enforce commit author email patterns
- `committer_email_pattern` - Enforce committer email patterns

Then run `terraform plan` to preview and `terraform apply` to apply.

**Subscription tier limitations:**

Rulesets availability depends on your GitHub subscription:

- `free` - Repository rulesets only work on **public** repositories; org rulesets skipped
- `pro` - Repository rulesets work on public and private repos; org rulesets skipped
- `team` - Full ruleset support including org rulesets
- `enterprise` - Full feature set

Set your subscription tier in `config/config.yml`:

```yaml
subscription: free  # Options: free, pro, team, enterprise
```

If you configure rulesets for private repos on the free tier, they will be
automatically skipped (with a warning in the validation script output).

### Adding/managing organization members

> ⚠️ **High-risk feature.** Read all warnings before enabling.

Organization membership is managed via YAML files in `config/membership/`. Each file maps GitHub
usernames to their role (`member` or `admin`).

**SCIM/SSO conflict warning:** Do **NOT** enable membership management if your organization uses
SCIM or an IdP (Okta, Azure AD, GitHub Enterprise SCIM) for provisioning. Terraform and SCIM will
conflict and cause unpredictable membership changes.

1. Create or edit files in `config/membership/` with the format:

   ```yaml
   # config/membership/engineering.yml
   alice: member
   bob: member
   carol: admin
   ```

1. Enable membership management in your module call:

   ```hcl
   module "github_org" {
     source = "gjed/config-as-yaml/github"
     # ...
     membership_management_enabled = true
   }
   ```

1. Run `terraform plan` — carefully review any removals before applying

1. Run `terraform apply`

**Removing a member:** Delete their username from the YAML. On the next apply, Terraform will
remove them from the organization, revoking all private repo access and destroying private forks.
Always review `terraform plan` output before applying.

Only effective for organizations (`is_organization: true` in `config/config.yml`).
Has no effect on personal accounts.
If you configure org rulesets on a free or pro tier, they will be
automatically skipped (listed in the `skipped_org_rulesets` output).

### Configuring organization webhooks

Organization webhooks fire for events across **all** repositories in the organization — unlike
repository webhooks which are scoped to a single repo. They are ideal for centralized audit
logging, org-wide CI/CD notifications, and security monitoring.

1. Define the webhook in `config/webhook/` (reuses the same format as repo webhooks):

```yaml
# config/webhook/my-webhooks.yml
audit-logger:
  url: https://audit.example.com/github
  content_type: json
  secret: env:ORG_WEBHOOK_SECRET
  events:
    - repository   # Repo created, deleted, renamed, or visibility changed
    - member       # Member added or removed
    - team         # Team created, deleted, or modified
    - organization # Org member added, removed, or invited
  active: true
```

1. Reference the webhook by name in `config/config.yml`:

```yaml
org_webhooks:
  - audit-logger
```

1. Run `terraform plan` to preview, then `terraform apply`

**Important notes:**

- Org webhooks are **organization-only** — they are silently skipped when `is_organization: false`
- Webhooks must be defined in `config/webhook/` before they can be referenced in `org_webhooks`
- Secrets follow the same `env:VAR_NAME` pattern as repo webhooks; pass via `webhook_secrets` variable
- Org webhooks work on all GitHub subscription tiers (no tier gating)

### Managing security managers

Security managers are GitHub teams with read access to security alerts and advisories across all
repositories. Requires Team or Enterprise subscription.

1. Edit `config/config.yml` and add a `security` section:

   ```yaml
   security:
     security_manager_teams:
       - security-team
   ```

1. Ensure `subscription` is set to `team` or `enterprise` in `config/config.yml`

1. Teams must already exist — this module does not create teams

1. Run `terraform plan` to preview, then `terraform apply`

**Subscription tier limitations:**

Security manager roles require `team` or `enterprise` subscription. On `free` or `pro` plans,
the resources are silently skipped. The validation script will warn if teams are configured on
an unsupported tier.

**Note:** Uses `github_organization_role_team` with dynamic role ID lookup (the deprecated
`github_organization_security_manager` resource is not used).

### Importing existing repositories

```bash
./scripts/import-repo.sh <org-name> <repo-name>
```

## Development Workflow

1. Create/activate virtual environment: `source .venv/bin/activate`
1. Make changes to configuration files
1. Run `pre-commit run --all-files` before committing
1. Use `make plan` to preview Terraform changes
1. Use `make apply` to apply changes

## Commits

**Always run pre-commit before committing:**

```bash
source .venv/bin/activate
pre-commit run --all-files
```

**Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) format:**

```text
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:

- `feat` - New feature (correlates with MINOR in SemVer)
- `fix` - Bug fix (correlates with PATCH in SemVer)
- `docs` - Documentation only changes
- `style` - Formatting, missing semi colons, etc; no code change
- `refactor` - Code change that neither fixes a bug nor adds a feature
- `perf` - Code change that improves performance
- `test` - Adding missing tests or correcting existing tests
- `build` - Changes that affect the build system or external dependencies
- `ci` - Changes to CI configuration files and scripts
- `chore` - Other changes that don't modify src or test files

Breaking changes:

- Add `!` after type/scope: `feat!: breaking change`
- Or add footer: `BREAKING CHANGE: description`

Examples:

```text
feat(repos): add new-service repository
fix(config): correct visibility setting for internal repos
docs: update AGENTS.md with commit guidelines
chore: update pre-commit hooks
feat(repos)!: rename repository configuration keys

BREAKING CHANGE: `config_group` is now `groups` in repositories.yaml
```

OpenSpec commits:

- Adding a spec or change proposal: `feat(spec): add <name>`
- Updating a spec or change proposal: `refactor(spec): update <name>`
- Archiving a change: `chore(spec): archive <name>`

## Code Style

- Terraform files: Use `terraform fmt`
- YAML: 2-space indentation
- Markdown: Follow markdownlint rules (see `.markdownlint.yaml`)

## Testing Changes

Always run `terraform plan` before `terraform apply` to review changes. Pay special attention to:

- Visibility changes (private → public)
- Destructive operations
- Team permission changes
