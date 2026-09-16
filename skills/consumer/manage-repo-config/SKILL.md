---
name: manage-repo-config
description: >-
  Add, modify, or remove GitHub repositories managed by the gjed/config-as-yaml/github Terraform
  module. Use when editing YAML under config/ (repositories, groups, config.yml), assigning
  configuration groups, setting repository visibility or features, wiring rulesets or webhooks to
  a repository, or previewing the resulting Terraform changes. Triggers on "add a repo", "change
  repo settings", "make repo private/public", "assign groups", or any edit to
  config/repository/*.yml or config/group/*.yml.
---

# Manage repository configuration

All repository state is declared in YAML under `config/` and applied with Terraform. Never edit
Terraform resources directly for per-repository changes — edit YAML.

## Config layout

- `config/config.yml` — organization name, `subscription` tier (`free|pro|team|enterprise`),
  `is_organization`, global defaults, `org_webhooks`, `security` settings.
- `config/group/*.yml` — named configuration groups (e.g. `oss`, `internal`). A group is a bag of
  repository settings plus optional `rulesets:` and `webhooks:` lists.
- `config/repository/*.yml` — repository definitions. Files in immediate subdirectories are also
  loaded. Every file's top-level keys are repository names; duplicate names across files are a
  validation error.
- `config/ruleset/*.yml`, `config/webhook/*.yml`, `config/team/*.yml`,
  `config/membership/*.yml` — referenced by name from groups, repositories, or `config.yml`.

## Merge semantics

Settings are merged in order, later wins: global defaults → each group in the repository's
`groups:` list (in list order) → repository-specific keys. List-valued fields (`rulesets`,
`webhooks`) are concatenated across groups and the repository, not replaced.

## Adding a repository

1. Pick the target file in `config/repository/` (or create a new `.yml` there).
2. Add an entry:

   ```yaml
   my-service:
     description: "What it does"
     groups: ["base", "internal"]
   ```

3. Only add keys that differ from what the groups already provide. Check the group files first;
   do not duplicate inherited settings.

## Subscription tier gating

The module degrades gracefully but silently skips features the tier does not support. Check
`subscription` in `config/config.yml` before promising behavior:

- `free` — rulesets only on public repositories; org rulesets skipped.
- `pro` — repository rulesets on public and private; org rulesets skipped.
- `team`/`enterprise` — full support (org rulesets, security manager teams).

Skipped items surface in module outputs (e.g. `skipped_org_rulesets`) and validation warnings.

## Validate and plan

Always run, in order:

```bash
python3 scripts/validate-config.py
terraform plan -out=tfplan   # or: make plan / make plan-repo REPO=my-service
```

Review the plan before any apply — especially visibility changes (private → public), destroys,
and permission changes. For a structured review, use the `plan-safety-review` skill.

## Provider semantics (optional MCP)

If a Terraform Registry MCP server (e.g. `terraform` from the repo's `.mcp.json`) is available,
look up the resource documentation for the **pinned provider version** (`integrations/github`,
pinned in `main.tf` / lockfile) before reasoning about attribute behavior — provider majors change
attribute semantics. Without the MCP, consult the registry docs on the web for the pinned
version; do not answer from memory.
