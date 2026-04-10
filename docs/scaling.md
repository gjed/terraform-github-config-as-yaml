# Scaling Guide

This guide covers API rate limit considerations, provider tuning, and the
repository partitioning feature for managing large GitHub organisations with
this module.

## API Cost Per Repository

Each `terraform plan` (or `apply`) triggers a read refresh for every repository
in scope. The following resources are read per repository:

| Resource | API calls | Notes |
|---|---|---|
| `github_repository` | 1 | Core repository data |
| `github_team_repository` | 1 per team | Varies by team count per repo |
| `github_repository_collaborator` | 1 per collaborator | Varies by collaborator count |
| `github_repository_ruleset` | 1 per ruleset | Varies by ruleset count |
| `github_actions_repository_permissions` | 1 | Only when actions config is set |
| `github_repository_webhook` | 1 per webhook | Varies by webhook count |

**Typical baseline:** ~7 API calls per repository (1 repo + 2 teams + 1 collaborator
+ 1 ruleset + 1 actions + 1 webhook). Repos with no teams, rulesets, or webhooks
cost as few as 1–2 calls.

## Rate Limit Thresholds

GitHub enforces per-hour rate limits on authenticated API requests:

| Auth method | Limit |
|---|---|
| Personal Access Token (PAT) | 5,000 requests / hour |
| GitHub App installation token | 15,000 requests / hour |

Estimated total API calls for a single `terraform plan` at various org sizes
(assuming ~7 calls per repo):

| Repositories | Estimated calls | Within PAT limit | Within App limit |
|---|---|---|---|
| 100 | ~700 | ✅ Yes | ✅ Yes |
| 500 | ~3,500 | ✅ Yes | ✅ Yes |
| 700 | ~4,900 | ⚠️ Near limit | ✅ Yes |
| 1,000 | ~7,000 | ❌ Exceeds | ✅ Yes |
| 2,000 | ~14,000 | ❌ Exceeds | ⚠️ Near limit |
| 2,500+ | ~17,500+ | ❌ Exceeds | ❌ Exceeds |

**Recommendation:** Use a GitHub App token for organisations with 500+ repositories.
For 2,000+ repositories, combine App tokens with repository partitioning.

## Provider Tuning

The `integrations/github` Terraform provider supports configurable delays between
API calls to avoid hitting rate limits. Add these to your `provider "github"` block:

### Small organisations (< 100 repositories)

```hcl
provider "github" {
  owner = "your-org"
  # No delays needed at this scale
}
```

### Medium organisations (100–500 repositories)

```hcl
provider "github" {
  owner          = "your-org"
  read_delay_ms  = 0
  write_delay_ms = 100
}
```

### Large organisations (500+ repositories)

```hcl
provider "github" {
  owner          = "your-org"
  read_delay_ms  = 50   # Spread read refreshes across time
  write_delay_ms = 250  # More conservative on writes
}
```

> **Note:** Delays slow down plan and apply times proportionally. A `read_delay_ms`
> of 50 ms with 1,000 repositories adds ~50 seconds to every plan. Balance delay
> against your CI timeout budget.

## Repository Partitioning

Partitioning lets you scope a Terraform plan to a subset of repositories, reducing
API consumption in proportion to the fraction of repos in the partition.

### Directory Layout

Organise your repository config files into subdirectories under `config/repository/`.
Each subdirectory is a named partition:

```text
config/repository/
├── common.yml          # Always loaded (not a partition)
├── infra/
│   ├── ci-tooling.yml
│   └── platform-services.yml
├── product/
│   ├── frontend.yml
│   └── backend.yml
└── legacy/
    └── old-services.yml
```

Top-level `*.yml` files (like `common.yml`) are **always** loaded regardless of
which partitions are selected.

### Selecting Partitions

Pass the `repository_partitions` variable to the module. An empty list (the
default) loads all partitions — identical to the pre-partitioning behaviour.

```hcl
module "github_org" {
  source  = "gjed/config-as-yaml/github"
  version = "~> 1.0"

  config_path = "${path.root}/config"

  # Load only the infra and product partitions
  repository_partitions = ["infra", "product"]
}
```

Setting `repository_partitions = []` (or omitting it) loads everything.

> **⚠️ Warning — Partition switching causes destroy plans**
>
> When you change `repository_partitions` from `[]` (all repos) to `["infra"]`,
> repositories in other partitions (`product`, `legacy`) disappear from
> Terraform's view. Terraform will plan to **destroy** their resources.
>
> Always verify the plan output before applying when narrowing the partition
> selection. Use repository deletion protection (see issue #37) as a safety net.
> The `detect-partitions.sh` script is designed to help CI avoid accidental
> partition narrowing.

### CI Integration with `detect-partitions.sh`

The `scripts/detect-partitions.sh` helper maps git changes to the affected
partitions, so CI only plans the partitions that actually changed.

**Basic usage:**

```bash
# Show which partitions changed between main and the current branch
./scripts/detect-partitions.sh main...HEAD

# Output as a JSON array for use as a Terraform variable
./scripts/detect-partitions.sh --tfvar main...HEAD
```

**GitHub Actions example:**

```yaml
jobs:
  detect:
    runs-on: ubuntu-latest
    outputs:
      partitions: ${{ steps.detect.outputs.partitions }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Required for git diff across branches

      - name: Detect affected partitions
        id: detect
        run: |
          partitions=$(./scripts/detect-partitions.sh --tfvar main...HEAD)
          echo "partitions=$partitions" >> "$GITHUB_OUTPUT"

  plan:
    needs: detect
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Terraform plan (scoped to affected partitions)
        env:
          TF_VAR_repository_partitions: ${{ needs.detect.outputs.partitions }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          terraform init
          terraform plan
```

**Escalation rules:**

| Changed files | Partitions planned |
|---|---|
| `config/group/*.yml` | All partitions |
| `config/ruleset/*.yml` | All partitions |
| `config/webhook/*.yml` | All partitions |
| `config/config.yml` | All partitions |
| `config/repository/<partition>/*.yml` | Only the changed partitions |
| `config/repository/*.yml` (top-level) | None (always loaded) |
| Non-config files only | None |

Shared config (groups, rulesets, webhooks, `config.yml`) can affect any
repository, so changes there require planning all partitions.
