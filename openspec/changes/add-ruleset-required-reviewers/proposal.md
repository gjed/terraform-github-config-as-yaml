## Why

GitHub rulesets can require approval from specific teams for matching files (`required_reviewers` on
the `pull_request` rule, currently in beta). The `integrations/github` provider exposes it on both
`github_repository_ruleset` and `github_organization_ruleset` (verified against provider 6.12.0 and
6.13.0 schemas). This module drops it silently: a `required_reviewers` key in YAML is ignored,
because the typed repository ruleset variable has no such attribute and neither ruleset resource
maps it.

The provider takes a numeric team ID. Hardcoding it in YAML does not work for the teams this module
creates, because their IDs do not exist until apply, and it makes configs unreadable everywhere else.
Reviewers must therefore be resolvable from a team slug, the identifier every other part of this
configuration already uses (`teams:` on repositories, `security_manager_teams`, `config/team/`).

## What Changes

- Accept `required_reviewers` on the `pull_request` rule of repository and organization rulesets,
  passing it through to the provider.
- A reviewer is identified either by `slug` (resolved to a team ID at plan/apply time) or by a
  numeric `id`. Exactly one is required. `type` defaults to `Team`, the only value GitHub supports.
- Slug resolution is dynamic:
  - slugs of teams defined in `config/team/` resolve from the module's own team resources, so a team
    and a ruleset that requires it can be created in the same apply;
  - any other slug is resolved with a `github_team` data source, which fails the plan with a clear
    error when the team does not exist.
- Validate `required_reviewers` in `scripts/validate-config.py`.
- Document the parameter and add examples.

## Impact

- Affected specs: `repository-management`, `org-ruleset-management`
- Affected code: `modules/repository/variables.tf`, `modules/repository/main.tf`, `main.tf`,
  `yaml-config.tf`, `scripts/validate-config.py`, `tests/`
- Affected docs: `wiki/Configuration-Reference.md`, `config/ruleset/default-rulesets.yml`,
  `AGENTS.md`, `skills/ruleset-authoring/SKILL.md`
- No breaking change. The provider floor stays at `>= 6.12.0`. The new `team_ids` input of
  `modules/repository` is optional and defaults to an empty map.
- Not covered by the e2e fixture: it would need a real team in the e2e organization.
