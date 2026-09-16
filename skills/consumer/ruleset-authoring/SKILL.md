---
name: ruleset-authoring
description: >-
  Author GitHub repository and organization rulesets in config/ruleset/*.yml for the
  gjed/config-as-yaml/github Terraform module. Use when creating or editing branch/tag
  protection rules, requiring pull request reviews or status checks, blocking force pushes,
  enforcing commit conventions, or when the user mentions rulesets, branch protection, required
  reviews, or signed commits.
---

# Ruleset authoring

Rulesets are defined once in `config/ruleset/*.yml` and referenced by name. Two scopes exist
with different assignment models — picking the wrong one is the most common mistake.

## Repository vs organization rulesets

- **Repository ruleset** (`scope: repository` or no `scope`): applied per-repository. Assigned
  via a `rulesets:` list in a group (`config/group/*.yml`) or a repository entry
  (`config/repository/*.yml`).
- **Organization ruleset** (`scope: organization`): applied org-wide, targeting repositories via
  `conditions.repository_name` include/exclude patterns. NOT assignable per-repo or per-group —
  it applies by pattern only. Requires `team` or `enterprise` subscription.

## Structure

```yaml
my-protection:
  # scope: organization      # only for org rulesets
  target: branch              # or: tag
  enforcement: active         # active | evaluate | disabled
  conditions:
    ref_name:
      include: ["~DEFAULT_BRANCH"]   # ~DEFAULT_BRANCH / ~ALL / refs/heads/... patterns
      exclude: []
    # repository_name:        # org rulesets only
    #   include: ["*"]
    #   exclude: ["sandbox-*"]
  rules:
    - type: deletion
    - type: non_fast_forward
    - type: pull_request
      parameters:
        required_approving_review_count: 1
        dismiss_stale_reviews_on_push: true
```

Supported rule types: `deletion`, `non_fast_forward`, `required_linear_history`,
`required_signatures`, `pull_request`, `required_status_checks`, `creation`, `update`,
`branch_name_pattern`, `commit_message_pattern`, `commit_author_email_pattern`,
`committer_email_pattern`, and `required_deployments` (repository rulesets only).

## Tier gating

Check `subscription` in `config/config.yml` first:

- `free` — repository rulesets apply to **public** repositories only; rulesets on private repos
  and all org rulesets are skipped (surfaced via warnings and the `skipped_org_rulesets`
  output).
- `pro` — repository rulesets on public and private repos; org rulesets still skipped.
- `team` / `enterprise` — full support.

Never silently author a ruleset the tier cannot enforce — tell the user it will be skipped.

## Workflow

1. Define or edit the ruleset in `config/ruleset/`.
2. For repository rulesets, reference it under `rulesets:` in the target group(s) or
   repository entries. For org rulesets, set `scope: organization` and the
   `repository_name` conditions instead — no references.
3. `python3 scripts/validate-config.py`
4. `terraform plan` and review (see `plan-safety-review` skill) — enforcement drops and ruleset
   deletions are blocking findings.

## Exact parameter schemas (optional MCP)

Rule `parameters` blocks mirror the provider schema, which changes between provider versions. If
a Terraform Registry MCP server (`terraform` in the repo's `.mcp.json`) is available, fetch the
`github_repository_ruleset` / `github_organization_ruleset` docs for the pinned
`integrations/github` version before writing non-trivial parameters. Otherwise verify against
the registry docs on the web for that version; do not rely on memorized schemas.
