## Context

`pull_request` is mapped in two places: `modules/repository/main.tf` (repository rulesets, typed
input in `variables.tf`) and root `main.tf` (organization rulesets, untyped decoded YAML). Both need
the new block. The two paths behave differently around null: inside the typed object an omitted
attribute exists and is `null`, so `lookup(parameters, key, fallback)` returns `null` and not the
fallback. This is the same trap already fixed for `required_checks`.

The provider requires `reviewer.id` as a number. Teams created by this module are
`module.teams_root`, `module.teams_level_1` and `module.teams_level_2`, each exposing `team_id`.
Their YAML key is the team name and therefore its slug.

## Goals / Non-Goals

**Goals:**

- Reviewers declared by team slug, including teams created in the same apply
- Same YAML shape for repository and organization rulesets
- Numeric `id` still accepted, for teams outside the organization's slug namespace or for users who
  already have the ID

**Non-Goals:**

- Resolving anything other than teams (the provider supports only `Team`)
- Verifying that a team has write access to the repository (GitHub enforces it; documented only)
- An e2e fixture entry (needs a real team in the e2e organization)
- Raising the provider constraint (6.12.0 already contains the block)

## Decisions

### 1. Reviewer identified by `slug` or `id`

```yaml
required_reviewers:
  - reviewer:
      slug: security-team      # or: id: 1234567
    file_patterns: ["*"]
    minimum_approvals: 1
```

`type` is optional and defaults to `Team`. Exactly one of `slug` / `id` must be set; this is
enforced by `validate-config.py`. If both reach Terraform, `id` wins.

**Alternative considered:** `id` only, as in the issue. Rejected: unusable for module-managed teams
(no ID before apply) and inconsistent with how teams are referenced everywhere else.

### 2. Slug resolution lives in the root module and is passed down as `team_ids`

Root computes `reviewer_team_slugs`, the set of slugs referenced by `required_reviewers` across
`effective_rulesets` and `effective_org_rulesets`. It builds one `team_ids` map (slug to ID):

- slug in `local.all_teams` (and `is_organization`): `module.teams_*[slug].team_id`
- otherwise: `data.github_team.reviewers[slug].id`, with `for_each` over the remaining slugs

`modules/repository` receives `team_ids` (`map(string)`, default `{}`) and resolves with
`reviewer.id != null ? reviewer.id : tonumber(var.team_ids[reviewer.slug])`. A conditional is used
instead of `coalesce` because `coalesce` evaluates every argument, and indexing the map with a null
slug would error.

**Why not a data source for everything:** a managed team does not exist at plan time on first apply,
so the lookup would fail. Using the module output also gives Terraform the dependency edge, so the
ruleset is created after the team.

**Why not resolve in the repository module:** it has no provider-level view of the other modules'
teams. Resolution needs the root's `all_teams` and module outputs.

### 3. Typed input mirrors the provider schema

```hcl
required_reviewers = optional(list(object({
  reviewer = object({
    id   = optional(number)
    slug = optional(string)
    type = optional(string, "Team")
  })
  file_patterns     = list(string)
  minimum_approvals = number
})), [])
```

Defaulting the list to `[]` in the type avoids the null `for_each` described above. The organization
path reads untyped YAML, so it guards with `coalesce(lookup(..., []), [])` instead, covering a key
written with no value.

### 4. Validation split

`validate-config.py` checks shape (list of at most 15; `reviewer` mapping; exactly one of `slug` /
`id`; slug matches the existing slug regex; `id` an integer and not a bool; `type` is `Team`;
`file_patterns` a non-empty list of strings; `minimum_approvals` an integer from 0 to 10). It cannot
know whether a slug exists in the organization; that is the data source's job and fails the plan.

## Risks / Trade-offs

- **Beta GitHub feature**: the API may change; documented as beta.
- **Unknown slug**: fails at plan with the provider's "Not Found" error from `github_team`. Accepted:
  it is loud and early.
- **Personal accounts have no teams**: a slug reviewer there cannot resolve. Documented; the data
  source fails the plan.
- **Managed team slug vs name**: managed teams use the YAML key as the name. GitHub derives the slug
  from the name; keys already must match the slug regex, so they coincide.
- **Drift**: the provider reads `required_reviewers` back, so changes made in the UI show up in plan.
