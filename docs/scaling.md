# Scaling Guide

This guide covers API rate limit considerations, provider tuning, and the
repository partitioning feature for managing large GitHub organisations with
this module.

## API Cost Per Repository

Each `terraform plan` (or `apply`) triggers a read refresh for every repository
in scope. The following resources are read per repository:

| Resource                                | API calls          | Notes                           |
| --------------------------------------- | ------------------ | ------------------------------- |
| `github_repository`                     | 1                  | Core repository data            |
| `github_team_repository`                | 1 per team         | Varies by team count per repo   |
| `github_repository_collaborator`        | 1 per collaborator | Varies by collaborator count    |
| `github_repository_ruleset`             | 1 per ruleset      | Varies by ruleset count         |
| `github_actions_repository_permissions` | 1                  | Only when actions config is set |
| `github_repository_webhook`             | 1 per webhook      | Varies by webhook count         |

**Typical baseline:** ~7 API calls per repository (1 repo + 2 teams + 1 collaborator

- 1 ruleset + 1 actions + 1 webhook). Repos with no teams, rulesets, or webhooks
  cost as few as 1–2 calls.

## Rate Limit Thresholds

GitHub enforces per-hour rate limits on authenticated API requests:

| Auth method                   | Limit                  |
| ----------------------------- | ---------------------- |
| Personal Access Token (PAT)   | 5,000 requests / hour  |
| GitHub App installation token | 15,000 requests / hour |

Estimated total API calls for a single `terraform plan` at various org sizes
(assuming ~7 calls per repo):

| Repositories | Estimated calls | Within PAT limit | Within App limit |
| ------------ | --------------- | ---------------- | ---------------- |
| 100          | ~700            | ✅ Yes           | ✅ Yes           |
| 500          | ~3,500          | ✅ Yes           | ✅ Yes           |
| 700          | ~4,900          | ⚠️ Near limit    | ✅ Yes           |
| 1,000        | ~7,000          | ❌ Exceeds       | ✅ Yes           |
| 2,000        | ~14,000         | ❌ Exceeds       | ⚠️ Near limit    |
| 2,500+       | ~17,500+        | ❌ Exceeds       | ❌ Exceeds       |

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

## Reducing plan cost with `-refresh=false`

The simplest and safest way to reduce plan API cost is to skip the full refresh on
routine PR/merge plans and rely on a scheduled full-refresh plan as the drift-detection
authority.

**How it works:**

- PR/merge plans use `terraform plan -refresh=false` — this skips the API read for every
  resource that has not changed in config, cutting API usage by 70–80% on typical changes
- A scheduled job (e.g., nightly) runs a full-refresh plan with all data sources and
  resource refreshes enabled — this acts as the drift-detection authority and applies if changes are found
- No state migration needed; works on single shared states with zero destroy risk

**Example GitHub Actions:**

```yaml
jobs:
  plan-pr:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Terraform plan (PR, no refresh)
        run: |
          terraform init
          terraform plan -refresh=false

  plan-nightly:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'
    steps:
      - uses: actions/checkout@v4

      - name: Full refresh plan (drift detection)
        run: |
          terraform init
          terraform plan
```

**Recommendation:** Try `-refresh=false` on PR plans first. It eliminates most API cost
without any architectural changes. Move to repository partitioning only if even a
scheduled full-refresh plan exceeds your API limits (roughly 2,000+ repositories).

## Repository Partitioning

Repository partitioning is a **static state-sharding mechanism** for very large organizations
(2,000+ repositories) where even a scheduled full-refresh plan exceeds GitHub's API limits.
It requires a separate Terraform state per partition, not a dynamic selection within a single state.

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

**CRITICAL:** `repository_partitions` must be paired with a **dedicated Terraform state per partition**.
Each root module in each state selects exactly one partition value and keeps it constant.

```hcl
# infra-root/main.tf — manages only infra partition, in its own state
module "github_org" {
  source  = "gjed/config-as-yaml/github"
  version = "~> 1.0"

  config_path = "${path.root}/../config"

  # Set ONCE at bootstrap, never vary dynamically between plans in this state
  repository_partitions = ["infra"]
}
```

```hcl
# product-root/main.tf — manages only product partition, in its own state
module "github_org" {
  source  = "gjed/config-as-yaml/github"
  version = "~> 1.0"

  config_path = "${path.root}/../config"

  # Different state, different partition value
  repository_partitions = ["product"]
}
```

Each root module has its own backend (e.g., S3 bucket prefix, or separate Terraform Cloud workspace):

```hcl
# infra-root/backend.tf
terraform {
  cloud {
    organization = "my-org"
    workspaces {
      name = "github-infra-partition"
    }
  }
}
```

```hcl
# product-root/backend.tf
terraform {
  cloud {
    organization = "my-org"
    workspaces {
      name = "github-product-partition"
    }
  }
}
```

Setting `repository_partitions = []` (or omitting it) loads everything and is appropriate for
small to medium organizations where a single shared state is sufficient.

#### ⚠️ Warning — Narrowing against a shared state causes repository destruction

Changing `repository_partitions` from `[]` to `["infra"]` in a Terraform state that has
ever managed repositories outside `infra` will plan destruction of every other repository.
Terraform has no mechanism to leave an orphaned `for_each` instance untouched.

This is not preventable inside Terraform — the module emits a warning whenever you narrow
to a strict subset, but legitimate dedicated-per-partition states also trip this warning.
**The safe path is structural:** use dedicated per-partition root modules with constant
partition values, never vary `repository_partitions` dynamically against a shared state.
See docs/scaling.md "Repository Partitioning" and AGENTS.md for the state-sharding contract.

### CI Integration with `detect-partitions.sh`

The `scripts/detect-partitions.sh` helper maps git changes to the affected partitions.
Use its output to **select which per-partition root module directories to run**,
not to dynamically select partitions within a single state.

**Basic usage:**

```bash
# Show which partitions changed between main and the current branch
./scripts/detect-partitions.sh main...HEAD

# Output as a JSON array for use in CI matrices
./scripts/detect-partitions.sh --tfvar main...HEAD
```

**GitHub Actions example (multi-root per-partition model):**

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
    strategy:
      matrix:
        partition: ${{ fromJson(needs.detect.outputs.partitions) }}
    steps:
      - uses: actions/checkout@v4

      - name: Terraform plan (${{ matrix.partition }} partition)
        working-directory: ${{ matrix.partition }}-root
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          terraform init
          terraform plan
```

Each `${{ matrix.partition }}-root` directory (`infra-root/`, `product-root/`, etc.)
is an independent root module with its own `backend.tf` and constant `repository_partitions` value.

**Escalation rules:**

| Changed files                         | Partitions affected            |
| ------------------------------------- | ------------------------------ |
| `config/group/*.yml`                  | All partitions                 |
| `config/ruleset/*.yml`                | All partitions                 |
| `config/webhook/*.yml`                | All partitions                 |
| `config/config.yml`                   | All partitions                 |
| `config/repository/<partition>/*.yml` | Only the changed partitions    |
| `config/repository/*.yml` (top-level) | All partitions (always loaded) |
| Non-config files only                 | None                           |

Shared config (groups, rulesets, webhooks, `config.yml`) can affect any
repository, so changes there require planning all partitions.
