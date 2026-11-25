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
│   ├── secret/                       # Org Actions/Dependabot secrets and variables (optional)
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

### Decommissioning a repository

Repositories are **archived, not deleted**, on destroy. The `archive_on_destroy` variable defaults
to `true`, so when a repo is removed from Terraform's view the GitHub provider archives it (via the
API) instead of permanently deleting it. Leave the default alone in production; it is the safety net
against accidental, irreversible deletion.

To decommission a repository:

1. Remove its entry from `config/repository/*.yml`
1. Run `terraform plan` to preview, then `terraform apply` — the repository is archived
1. If you genuinely intend to permanently delete it, drop the archived repo from Terraform state
   (`./scripts/offboard-repos.sh <repo>`, or `terraform state rm` directly) and then delete it
   manually via the GitHub UI or API

`prevent_destroy` is intentionally not set: Terraform requires it to be a literal boolean, and
setting it `true` would deadlock normal `for_each`-based repo removal — every repo dropped from YAML
would trip a permanent plan error requiring manual state surgery.

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

**Required reviewers** (`pull_request` rule, beta GitHub feature): add `required_reviewers` under
`parameters`. Each entry sets `reviewer` (exactly one of `slug` or `id`; `type` defaults to `Team`),
`file_patterns` and `minimum_approvals` (0 = requested, not required; max 15 entries). A `slug` of a
team in `config/team/` resolves from the managed team; any other slug is looked up and the plan fails
if it does not exist. The team needs write access to the repository. Personal accounts have no teams.

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

### Managing secrets and variables

Actions secrets, Actions variables, and Dependabot secrets can be managed at the organization or
repository level. Secret values are never written in YAML: a secret's `value` must be an
`env:VAR_NAME` reference, and the value is supplied through the sensitive `secret_values`
Terraform variable (same pattern as `webhook_secrets`).

**State warning:** secret values are stored in Terraform state. Use an encrypted remote backend
(for example S3 with encryption, or Terraform Cloud) before managing secrets.

1. Organization-level definitions live in `config/secret/*.yml` (see `config/secret/examples.yml`).
   Each file may define `actions_secrets`, `actions_variables`, and `dependabot_secrets`. Files are
   merged per type by name, last file wins. Visibility is `all`, `private`, or `selected`; with
   `selected`, list the managed repositories in `selected_repositories`.

   ```yaml
   # config/secret/org-secrets.yml
   actions_secrets:
     DEPLOY_TOKEN:
       value: "env:DEPLOY_TOKEN"
       visibility: selected
       selected_repositories: [my-app, my-api]
   actions_variables:
     ENVIRONMENT:
       value: "production"
       visibility: all
   ```

1. Repository-level definitions go under `secrets:` and `variables:` in a group or repository.
   Groups apply in order, and a repository definition replaces a group definition with the same name.

   ```yaml
   secrets:
     actions:
       DATABASE_URL:
         value: "env:MY_REPO_DATABASE_URL"
     dependabot:
       REGISTRY_PASSWORD:
         value: "env:REGISTRY_PASSWORD"
   variables:
     actions:
       DEPLOY_ENV:
         value: "staging"
   ```

1. Pass the values through `secret_values` in the root module, for example
   `secret_values = { DEPLOY_TOKEN = var.deploy_token }`.

1. Names must match `^[A-Z_][A-Z0-9_]*$` and must not start with `GITHUB_`. Lowercase names are
   rejected because GitHub upper-cases them, which would cause a perpetual diff.

1. A missing `env:` key, invalid name, or unknown `selected_repositories` entry fails `terraform plan`.
   Error messages name the secret and the reference, never the value.

1. Run `terraform plan` to review the changes before applying.

### Managing environments

Repository environments are defined under `environments:` in a group or repository, keyed by
environment name. Groups apply in order, and a repository entry replaces a group entry with the
same name as a whole (properties are not merged, so an override cannot inherit group reviewers or
secrets by accident).

```yaml
environments:
  production:
    wait_timer: 10                  # minutes, 0-43200
    can_admins_bypass: true
    prevent_self_review: true
    reviewers:                      # at most 6 in total
      users: ["octocat"]            # logins
      teams: ["platform"]           # slugs
    deployment_branch_policy:
      custom_branch_policies: true  # or protected_branches: true, never both
      branch_patterns: ["main", "release/*"]
      tag_patterns: ["v*"]
    secrets:
      DEPLOY_TOKEN:
        value: "env:DEPLOY_TOKEN"
    variables:
      REGION:
        value: "eu-west-1"
```

1. `protected_branches` and `custom_branch_policies` are mutually exclusive, and `branch_patterns` and
   `tag_patterns` need `custom_branch_policies: true`, which in turn needs at least one pattern (an
   empty list would let nothing deploy). Both `scripts/validate-config.py` and a Terraform
   `precondition` enforce this. Each pattern becomes one deployment policy.

1. Team reviewers resolve like ruleset `required_reviewers`: a slug of a team in `config/team/`
   resolves from the managed team, any other slug is looked up and fails the plan if missing. User
   reviewers are looked up by login. GitHub rejects reviewers without access to the repository, so
   grant each reviewer team under `teams:` and each user under `collaborators:` on that repository;
   the environment is created after those grants.

1. Environment secrets follow the repository secret rules: `value` must be an `env:VAR_NAME`
   reference resolved from `secret_values`, names must match `^[A-Z_][A-Z0-9_]*$` and must not start
   with `GITHUB_`, and values are stored in Terraform state. Variable values are plaintext.

1. On the `free` subscription tier, the environments of private repositories are skipped as a
   whole, secrets and variables included, because environments, reviewers, wait timers and
   deployment branch policies on private repositories need a paid plan. The `skipped_environments`
   output lists them and `validate-config.py` warns. Public repositories keep their environments.

1. The `repository_environments` output lists environment, secret and variable names, never values.

1. Run `terraform plan` to review the changes before applying.

### Managing custom properties

Custom properties are organization-level metadata fields (for example `environment` or `compliance_level`)
that can be assigned to repositories and used to target org rulesets. Definitions live in
`config/custom-property/*.yml`, one property per top-level key, and values are assigned with
`custom_property_values:` in groups and repositories. See `config/custom-property/examples.yml` for all four types.

```yaml
# config/custom-property/properties.yml
environment:
  description: "Deployment environment"
  value_type: single_select       # string, single_select, multi_select or true_false
  required: true
  default_value: development      # required properties need a default or a value on every repository
  allowed_values: [development, staging, production]
tags:
  value_type: multi_select
  allowed_values: [frontend, backend, critical]
```

```yaml
# config/group/groups.yml and config/repository/repositories.yml
oss:
  custom_property_values:
    environment: production
    tags: [frontend]

my-repo:
  groups: ["oss"]
  custom_property_values:
    environment: staging          # overrides the group value
    tags: [backend, critical]     # replaces the group's list, it is not merged
```

1. Definitions take `description`, `value_type` (required), `required`, `default_value`, `allowed_values`
   (required for select types, not allowed for the others) and `values_editable_by` (`org_actors` or
   `org_and_repo_actors`). Files are merged in alphabetical order, and a property defined in two files
   raises a `check` warning and appears in `duplicate_key_warnings`; the last file wins.

1. Values merge like `teams:` and `collaborators:`: groups in order, then the repository, later values replace
   earlier ones by property name. Write a scalar for `string`, `single_select` and `true_false` and a list for
   `multi_select`; the module wraps scalars into the list the provider expects.

1. A required property is satisfied by a `default_value` (GitHub applies it to repositories without a value).
   A required property without a default must have a value on every managed repository, or the plan fails.

1. `scripts/validate-config.py` and Terraform preconditions reject an invalid `value_type`, `allowed_values` on a
   non-select type, a `default_value` outside `allowed_values`, undefined property names, values outside
   `allowed_values`, a list for a single-value type, and a missing required value.

1. Custom properties need an organization (`is_organization: true`) and work on every subscription tier.
   For a personal account the definitions and all assignments are skipped, the
   `skipped_custom_properties` output lists the skipped definitions and `validate-config.py` warns.
   `managed_custom_properties` lists the created definitions.

1. Property definitions are created before any repository assignment. Changing a property's `value_type` is
   planned as an in-place update, so the plan shows no replacement and GitHub may reject the change at apply
   time; review the plan first. `values_editable_by` defaults to `org_actors` when omitted.

1. Run `terraform plan` to review the changes before applying.

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

### Detecting drift

Drift is a difference between the real GitHub state and the configuration, caused by manual changes
(GitHub UI, `gh`, other API clients). `make drift-check` runs a full-refresh `terraform plan`
(`-detailed-exitcode`, never `-refresh=false`), converts it with `terraform show -json` and summarises it:

```bash
make drift-check                        # text report (coloured on a terminal)
make drift-check FORMAT=markdown        # for a PR comment or issue body
make drift-check REPO=my-repo           # one repository, same -target as plan-repo
./scripts/detect-drift.sh --format json --plan-file drift.tfplan
```

Run it where `terraform init` was done and `GITHUB_TOKEN` is set. `make` exports `TF_VAR_config_path`; when
calling the script directly from this repository's root, run `export TF_VAR_config_path="$PWD/config"` first,
or Terraform stops with "No value for required variable". The report goes to stdout; progress and Terraform
output go to stderr, so `--format json` can be piped.

The plan compares GitHub with the configuration, so it also lists configuration changes that are merged but
not yet applied; it does not read the plan's `resource_drift` section. Run it against applied configuration
to get a drift-only signal.

Exit codes of `scripts/detect-drift.sh`, decided from the plan JSON:

| Code | Meaning                                                           |
| ---- | ----------------------------------------------------------------- |
| 0    | No drift                                                          |
| 1    | Error (missing tool, failed plan, invalid plan JSON, bad option)  |
| 2    | Drift: the plan changes at least one resource                     |
| 3    | Critical drift: a `github_repository` would be destroyed/replaced |

The report groups changes by repository (organization-level resources last) and flags as critical any
destroy or replace of a `github_repository`, and any change that weakens security: visibility
`private`/`internal` to `public`, a branch protection or ruleset deleted or disabled, required signatures
removed. Sensitive values print as `(sensitive)`. The helper can also be used on its own:
`terraform show -json tfplan | python scripts/drift_report.py --format markdown`.

`make drift-check` shows the same report, but GNU make turns any failing recipe into exit status 2, so CI that
needs the exit codes must call the script directly.

A kept `--plan-file` contains sensitive values in clear text; treat it as a secret. Notifications,
auto-remediation and scheduled CI runs are not part of this script.

## CI/CD examples

`ci/` holds consumer templates, not this repository's own CI (that is `.github/workflows/`, whose job
names the main-branch ruleset requires: never rename them, and never put a template there):

- `ci/github-actions/terraform-pr.yml`, `terraform-apply.yml` and `terraform-drift.yml`
- `ci/jenkins/Jenkinsfile`, `ci/backends/*/backend.tf` and `ci/docs/authentication.md`

Rules for editing them: pin every action to a full commit SHA with a `# vX.Y.Z` comment (resolve it with
`gh api repos/<owner>/<action>/git/ref/tags/<tag>`), keep `permissions:` minimal, never use
`pull_request_target`, and keep the drift workflow calling `scripts/detect-drift.sh` directly rather than
`make drift-check` (make flattens the exit codes). `tests/test_ci_examples.py` enforces these.

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
