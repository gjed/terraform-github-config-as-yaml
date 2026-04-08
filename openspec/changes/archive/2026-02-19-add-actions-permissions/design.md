# Design: GitHub Actions Permissions Configuration

## Context

GitHub Actions permissions control which workflows can run and what they can access. These settings
are security-critical for supply chain protection. The Terraform GitHub provider offers several
resources for managing these permissions:

- `github_actions_repository_permissions` - Repository-level action restrictions
- `github_actions_organization_permissions` - Organization-level defaults

This feature must integrate with the existing YAML configuration pattern while providing secure defaults.

## Goals / Non-Goals

**Goals:**

- Enable GitOps management of Actions permissions alongside repository settings
- Provide secure defaults (principle of least privilege)
- Support both repository-level and organization-level configuration
- Maintain backward compatibility with existing configurations
- Handle subscription tier limitations gracefully

**Non-Goals:**

- Managing workflow files themselves (out of scope per project constraints)
- Environment-specific deployment permissions (deferred to future change)
- Self-hosted runner configuration (separate concern)

## Decisions

### Decision 1: Configuration Schema Location

**What:** Actions configuration lives as a nested block within repository/organization configuration.

**Why:** Follows existing patterns for teams, collaborators, and rulesets. Keeps related settings
together rather than introducing a new top-level configuration file.

```yaml
# Repository-level (repositories.yml)
my-repo:
  actions:
    enabled: true
    allowed_actions: selected
    # ...

# Organization-level (config.yml)
organization:
  actions:
    enabled_repositories: all
    # ...
```

### Decision 2: Allowed Actions Policy

**What:** Support three policies matching GitHub's options: `all`, `local_only`, `selected`.

**Alternatives considered:**

- Custom policy engine: Too complex, deviates from GitHub's model
- Only support `selected`: Would limit flexibility for trusted environments

**Rationale:** Direct mapping to GitHub's model reduces cognitive overhead and ensures full capability.

### Decision 3: Default Workflow Permissions

**What:** Default to `read` permissions for workflows, requiring explicit opt-in for `write`.

**Why:** Principle of least privilege. Workflows should only have write access when explicitly needed.
This aligns with GitHub's recommended security practices.

### Decision 4: Group Inheritance for Actions

**What:** Actions configuration inherits from groups using same merge strategy as other settings.

**Why:** Consistency with existing patterns. Organizations can define secure defaults in groups
that repositories inherit.

```yaml
# groups.yml
secure-defaults:
  actions:
    allowed_actions: selected
    allowed_actions_config:
      github_owned_allowed: true
      verified_allowed: true
```

### Decision 5: Organization vs Repository Settings (Policy Ceiling)

**What:** Organization-level Actions settings act as a **policy ceiling**, not defaults that
repositories can override.

**Why:** This matches GitHub's actual permission model. Organization settings restrict what
repositories can do; they cannot be escalated by repository settings.

**Behavior:**

| Org Setting                          | Repo Setting                | Result                                              |
| ------------------------------------ | --------------------------- | --------------------------------------------------- |
| `allowed_actions: local_only`        | `allowed_actions: all`      | **Error** or org wins (repo cannot escalate)        |
| `allowed_actions: all`               | `allowed_actions: selected` | Repo wins (more restrictive is allowed)             |
| `default_workflow_permissions: read` | `write`                     | Depends on org's `can_approve_pull_request_reviews` |

**Implementation approach:**

- Document that org settings are enforced by GitHub, not by our Terraform
- Repository settings that violate org policy will fail at `terraform apply` time (GitHub API error)
- Consider adding validation to warn users before apply

**Note:** This differs from our group inheritance model where repository settings override group
settings. Organization Actions settings are enforced by GitHub itself, not our configuration layer.

### Decision 6: Subscription Tier Handling

**What:** Skip unsupported features for lower subscription tiers with warnings, similar to ruleset handling.

**Why:** Graceful degradation prevents Terraform errors while informing users of limitations.

## Risks / Trade-offs

| Risk                                           | Mitigation                                                 |
| ---------------------------------------------- | ---------------------------------------------------------- |
| Overly permissive defaults expose supply chain | Default to `read` permissions and require explicit `write` |
| Configuration complexity                       | Provide sensible defaults; full config is optional         |
| API rate limits from many permission resources | Batch where possible; document rate limit considerations   |
| Breaking changes if GitHub API changes         | Pin provider version; follow semver for this project       |

## Configuration Schema

### Repository-Level Actions Configuration

```yaml
actions:
  # Enable/disable Actions for this repository
  enabled: true  # default: true

  # Which actions are allowed to run
  # Options: all, local_only, selected
  allowed_actions: selected  # default: all

  # Configuration when allowed_actions is "selected"
  allowed_actions_config:
    github_owned_allowed: true    # Allow actions in github/* namespace
    verified_allowed: true        # Allow marketplace verified creators
    patterns_allowed:             # Explicit patterns to allow
      - "actions/*"
      - "myorg/*"

  # Default permissions for GITHUB_TOKEN in workflows
  # Options: read, write
  default_workflow_permissions: read  # default: read

  # Whether Actions can approve pull request reviews
  can_approve_pull_request_reviews: false  # default: false
```

### Organization-Level Actions Configuration

```yaml
organization:
  actions:
    # Which repositories can use Actions
    # Options: all, none, selected
    enabled_repositories: all

    # Default allowed actions policy for org
    allowed_actions: selected

    # Same structure as repository-level
    allowed_actions_config:
      github_owned_allowed: true
      verified_allowed: true
      patterns_allowed:
        - "actions/*"

    # Default workflow permissions for org
    default_workflow_permissions: read
    can_approve_pull_request_reviews: false
```

## Terraform Resource Mapping

| Configuration            | Terraform Resource                        | Notes           |
| ------------------------ | ----------------------------------------- | --------------- |
| Repository `actions.*`   | `github_actions_repository_permissions`   | Per-repository  |
| Organization `actions.*` | `github_actions_organization_permissions` | Single resource |

## Open Questions

1. **Fork PR workflow settings:** The issue mentions `fork_pull_request_workflows` configuration.
   The `github_actions_repository_permissions` resource doesn't directly expose this. Should we:

   - Defer this to a future enhancement?
   - Use a different resource/approach?

   **Recommendation:** Defer to future change. Focus on core permissions first.

1. **Repository access level:** The `github_actions_repository_access_level` resource controls which
   other repositories can access Actions in a repository. Should this be included?

   **Recommendation:** Defer to future change to keep scope manageable.
