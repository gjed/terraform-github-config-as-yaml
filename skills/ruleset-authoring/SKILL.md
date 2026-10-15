---
name: ruleset-authoring
description: >-
  Create or modify GitHub rulesets (branch/tag protection rules) in a config-as-yaml repo. Use
  when editing config/ruleset/, assigning rulesets to groups or repositories, choosing between
  repository-scoped and organization-scoped rulesets, or when the user asks to "protect main",
  "require reviews", or "enforce signed commits".
---

# Ruleset authoring

Rulesets live in `config/ruleset/*.yml`. Two scopes with different assignment models:

- **Repository rulesets** (`scope: repository` or omitted): assigned per repo/group via a
  `rulesets:` list in `config/group/*.yml` or `config/repository/*.yml`.
- **Organization rulesets** (`scope: organization`): applied org-wide, filtered by
  `repository_name` include/exclude patterns in `conditions`. NOT assignable via `rulesets:`.

## Repository ruleset shape

```yaml
oss-main-protection:
  target: branch          # branch | tag
  enforcement: active     # active | evaluate | disabled
  conditions:
    ref_name:
      include: ["~DEFAULT_BRANCH"]
      exclude: []
  rules:
    - type: deletion
    - type: non_fast_forward
    - type: pull_request
      parameters:
        required_approving_review_count: 1
        dismiss_stale_reviews_on_push: true
```

Assign it: `rulesets: [oss-main-protection]` on a group or repository.

## Organization ruleset shape

Add `scope: organization` and optionally `repository_name` conditions
(`include: ["*"]`, `exclude: ["sandbox-*"]`). Requires `team` or `enterprise` subscription;
on `free`/`pro` they are skipped and listed in the `skipped_org_rulesets` output.

## Supported rule types

`deletion`, `non_fast_forward`, `required_linear_history`, `required_signatures`,
`pull_request`, `required_status_checks`, `creation`, `update`, `required_deployments`
(repository scope only), `branch_name_pattern`, `commit_message_pattern`,
`commit_author_email_pattern`, `committer_email_pattern`.

## Required reviewers (beta)

Add `required_reviewers` to a `pull_request` rule's `parameters` (repository and org rulesets):

```yaml
    - type: pull_request
      parameters:
        required_approving_review_count: 1
        required_reviewers:
          - reviewer:
              slug: security-team    # OR id: 1234567 (exactly one); type defaults to Team
            file_patterns: ["*.tf", "security/**"]
            minimum_approvals: 1     # 0 = requested for review, not required
```

- `slug` of a team in `config/team/` resolves from the managed team (same apply). Any other slug is
  looked up; the plan fails if the team does not exist.
- The team needs write access to the repository.
- Beta GitHub feature. Personal accounts have no teams, so this does not apply there.
- Max 15 entries; `minimum_approvals` 0-10; `type`, if set, must be `Team`.

## Tier gating

- `free`: repository rulesets work on **public** repos only; private-repo assignments are
  skipped with a warning
- `pro`: repository rulesets on public and private; org rulesets skipped
- `team` / `enterprise`: everything

## Workflow

1. Edit/create the ruleset in `config/ruleset/`, reference it from groups/repos.
2. `python3 scripts/validate-config.py` — catches unknown rule types, bad references, and
   tier conflicts.
3. `make plan`, then review with the `plan-safety-review` skill. Deleting or renaming a
   ruleset key plans a destroy of the live ruleset — renames are destroy+create.

For exact parameter semantics of `github_repository_ruleset` /
`github_organization_ruleset` under the pinned provider (`integrations/github >= 6.12.0`),
prefer the Terraform Registry MCP server from `.mcp.json`; otherwise use the provider docs on
registry.terraform.io.
