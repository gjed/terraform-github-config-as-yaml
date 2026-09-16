# Scaling Guide

This guide covers API rate limit considerations, provider tuning, and plan-cost
reduction for managing large GitHub organisations with this module.

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
For 2,000+ repositories, combine App tokens with `-refresh=false` on routine plans.

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

**Recommendation:** Use `-refresh=false` on PR plans. It eliminates most API cost
without any architectural changes. If even a scheduled full-refresh plan exceeds your
API limits, switch to a GitHub App installation token (15,000 requests/hour) and
increase `read_delay_ms` to spread the refresh over time.

## Organizing repository files

Repository YAML files can be organized into one level of subdirectories under
`config/repository/` for readability. All files are always loaded — subdirectories
carry no selection semantics:

```text
config/repository/
├── common.yml          # Loaded
├── infra/
│   ├── ci-tooling.yml  # Loaded
│   └── platform.yml    # Loaded
└── product/
    └── frontend.yml    # Loaded
```

Duplicate repository names are detected across all loaded files, regardless of
which directory defines them.
