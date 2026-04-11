# Design: Add Branch Protection

## Overview

Add support for traditional GitHub branch protection rules alongside the existing ruleset system.
The design mirrors the rulesets pattern: named definitions in a dedicated config directory,
referenced from groups and repositories, merged using the same inheritance strategy.

## Architecture

### Configuration Layer

New directory `config/branch-protection/` containing `.yml` files. Each top-level key is a named
branch protection rule.

```yaml
# config/branch-protection/default-protections.yml
main-protection:
  pattern: "main"
  enforce_admins: true
  allows_deletions: false
  allows_force_pushes: false
  lock_branch: false
  require_conversation_resolution: true
  require_signed_commits: false
  required_linear_history: false

  required_pull_request_reviews:
    required_approving_review_count: 1
    dismiss_stale_reviews: true
    require_code_owner_reviews: false
    require_last_push_approval: false
    restrict_dismissals: false
    dismissal_restrictions:
      users: []
      teams: []
      apps: []
    pull_request_bypassers:
      users: []
      teams: []
      apps: []

  required_status_checks:
    strict: true
    contexts:
      - "ci/build"

  restrict_pushes:
    blocks_creations: true
    push_allowances:
      users: []
      teams: []
      apps: []
```

**Field defaults:** Only `pattern` is required. All boolean fields default to `false` or a
reasonable secure default. Sub-blocks (`required_pull_request_reviews`, `required_status_checks`,
`restrict_pushes`) are optional — omitting them means that feature is not configured.

### YAML Parsing Layer (`yaml-config.tf`)

New locals following the rulesets pattern:

- `branch_protection_config_path` — path to `config/branch-protection/`
- `branch_protection_files` — fileset of `*.yml` in that directory
- `branch_protection_configs_by_file` — per-file parsed YAML (for duplicate detection)
- `branch_protection_key_occurrences` / `duplicate_branch_protection_keys` — duplicate detection
- `branch_protections_config` — merged map of all branch protection definitions
- `merged_branch_protections` — per-repo map of resolved protections (from groups + repo)

Merging strategy (identical to rulesets):

1. Iterate `repo_config.groups` in order, collect `branch_protections` lists
1. Append repo-level `branch_protections`
1. For each name, look up in `branch_protections_config`
1. Deduplicate by name (later overrides earlier)

**No subscription tier filtering.** Branch protection works on all tiers including free-tier
private repos.

**Validation:** Reference to an undefined branch protection name produces a Terraform error
via a `check` block (same pattern as undefined ruleset references).

**Directory optionality:** The `config/branch-protection/` directory is optional. If missing,
the system uses an empty map and no branch protections are created. This matches the webhook
directory behavior (not the ruleset directory which is required).

### Module Layer (`modules/repository/`)

New variable in `variables.tf`:

```hcl
variable "branch_protections" {
  description = "Map of branch protection rules to apply"
  type = map(object({
    pattern                         = string
    enforce_admins                  = optional(bool, false)
    allows_deletions                = optional(bool, false)
    allows_force_pushes             = optional(bool, false)
    lock_branch                     = optional(bool, false)
    require_conversation_resolution = optional(bool, false)
    require_signed_commits          = optional(bool, false)
    required_linear_history         = optional(bool, false)

    required_pull_request_reviews = optional(object({
      required_approving_review_count = optional(number, 1)
      dismiss_stale_reviews           = optional(bool, false)
      require_code_owner_reviews      = optional(bool, false)
      require_last_push_approval      = optional(bool, false)
      restrict_dismissals             = optional(bool, false)
      dismissal_restrictions = optional(object({
        users = optional(list(string), [])
        teams = optional(list(string), [])
        apps  = optional(list(string), [])
      }))
      pull_request_bypassers = optional(object({
        users = optional(list(string), [])
        teams = optional(list(string), [])
        apps  = optional(list(string), [])
      }))
    }))

    required_status_checks = optional(object({
      strict   = optional(bool, false)
      contexts = optional(list(string), [])
    }))

    restrict_pushes = optional(object({
      blocks_creations = optional(bool, true)
      push_allowances = optional(object({
        users = optional(list(string), [])
        teams = optional(list(string), [])
        apps  = optional(list(string), [])
      }))
    }))
  }))
  default = {}
}
```

New resource in `main.tf`:

```hcl
resource "github_branch_protection" "this" {
  for_each = var.branch_protections

  repository_id = github_repository.this.node_id
  pattern       = each.value.pattern

  enforce_admins                  = each.value.enforce_admins
  allows_deletions                = each.value.allows_deletions
  allows_force_pushes             = each.value.allows_force_pushes
  lock_branch                     = each.value.lock_branch
  require_conversation_resolution = each.value.require_conversation_resolution
  require_signed_commits          = each.value.require_signed_commits
  required_linear_history         = each.value.required_linear_history

  dynamic "required_pull_request_reviews" { ... }
  dynamic "required_status_checks" { ... }
  dynamic "restrict_pushes" { ... }
}
```

Dynamic blocks are only created when the corresponding sub-object is non-null in the YAML
definition.

### Root Module (`main.tf`)

Pass-through to the repository module:

```hcl
branch_protections = each.value.branch_protections
```

### Resource Keying

The `for_each` key is the protection name (e.g., `main-protection`). This means:

- Resource address: `github_branch_protection.this["main-protection"]`
- A repo can have multiple protections targeting different branch patterns
- Renaming a protection definition requires a state move

## Trade-offs

- **Rulesets vs branch protection overlap:** GitHub allows both on the same branch. The effective
  policy is the union of both. This module does not prevent or warn about overlap — that is left
  to the user's judgment.
- **Optional directory:** Unlike `config/ruleset/` (required), `config/branch-protection/` is
  optional. Existing users who do not need branch protection are unaffected.
- **No template system:** Unlike rulesets which have a template/override mechanism, branch
  protections are referenced by name only. Adding templates can be a follow-up change if needed.
