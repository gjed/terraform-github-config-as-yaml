## Context

Repository-level secrets and variables (`secrets-and-variables-management`) already show the pattern this change
follows: YAML in groups and repositories is merged per repository in `yaml-config.tf`, `env:VAR_NAME` values are
resolved from `secret_values`, the typed result is passed to `modules/repository`, and the module guards each
resource with `lifecycle.precondition`. Ruleset `required_reviewers` already resolve team slugs to IDs through
`local.reviewer_team_ids` and a `github_team` data source.

## Goals / Non-Goals

**Goals:**

- Manage environments, their protection rules, deployment policies, secrets and variables from YAML.
- Reuse the existing merge, `env:` resolution and team resolution code; add no second resolver.
- Fail at plan time for configurations that cannot work, without leaking secret values.

**Non-Goals:**

- Moving this repository's own `e2e` environment into the configuration repository.
- Environment-level Dependabot secrets (GitHub has none).
- Custom deployment protection rules (GitHub App based) and environment-scoped org secrets.

## Decisions

### 1. Merge by environment name, whole-definition replacement

Environments merge like `secrets:` and `variables:`: groups in order, then the repository, later definitions
replace earlier ones by environment name. Properties are not deep-merged. A partial override such as changing
only `wait_timer` would silently inherit reviewers or secrets from the group, which is the wrong default for
access-control settings.

### 2. Skip the whole environment on free-tier private repositories

GitHub documents environments, reviewers, wait timers and deployment branch policies on private repositories as
paid features. Skipping only the protection rules would still create an unprotected environment holding
secrets, which is worse than no environment, so the whole environment is skipped, like
`effective_branch_protections`. The skip is reported in the `skipped_environments` output and by a warning from
`validate-config.py`. The alternative of failing the apply was rejected to stay consistent with rulesets and
branch protections.

### 3. User reviewers resolve through a `github_user` lookup

The provider takes numeric IDs for reviewers. Teams reuse `local.reviewer_team_slugs` and
`local.reviewer_team_ids`, which now also include environment team reviewers. Users have no equivalent, so a
`github_user` data source keyed by login supplies `local.environment_reviewer_user_ids`. Both are limited to
environments that are applied, so skipped environments cause no lookups.

### 4. `protected_branches` and `custom_branch_policies` checked twice

`validate-config.py` rejects the combination for fast feedback. A `precondition` on the environment resource
rejects it again so module consumers who bypass the script still get an error rather than an opaque API
failure. The same two places reject patterns given without `custom_branch_policies: true`, and a `wait_timer`
outside 0-43200.

### 5. One deployment policy resource per pattern

`github_repository_environment_deployment_policy` accepts exactly one of `branch_pattern` and `tag_pattern`, so
the module flattens `branch_patterns` and `tag_patterns` into a map keyed `<environment>/branch:<pattern>` and
`<environment>/tag:<pattern>`. A deployment branch policy block is only emitted when one of the two flags is
true, because the API rejects a policy with both false.

### 6. Environment secrets and variables are flattened into maps keyed `<environment>/<NAME>`

This keeps them as plain `for_each` resources next to the repository-level ones and lets the preconditions name
both the environment and the secret. `secret_names`-style outputs return names only.

## Risks / Trade-offs

- **[Risk] Secret values in state**: same as repository secrets; documentation points at encrypted backends.
- **[Risk] Free tier skip hides a security setting**: mitigated by the `skipped_environments` output and the
  script warning; documented in the spec.
- **[Trade-off] Whole-definition replacement**: repeating reviewers when overriding one property is more verbose
  but cannot widen access by accident.
- **[Trade-off] Tier gate is coarse**: the free tier also offers some environment features on private
  repositories in practice, but gating on the documented requirement avoids partial, hard-to-explain applies.
