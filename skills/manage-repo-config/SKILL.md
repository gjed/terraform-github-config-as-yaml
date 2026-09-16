---
name: manage-repo-config
description: >-
  Add, modify, or remove a repository managed by the config-as-yaml Terraform module. Use when
  editing files under config/repository/, assigning configuration groups, changing repository
  settings (visibility, merge strategies, topics, teams, webhooks), or when the user asks to
  "add a repo", "make repo X private", or "put repo Y in the oss group".
---

# Manage repository configuration

Repositories are declared in YAML under `config/repository/` (top-level `*.yml` files and
one level of subdirectories, all always loaded). Terraform reads them directly; there is no
generation step.

## Workflow

1. Find the repo's YAML entry: search `config/repository/` for the repository name.
   New repos go into an existing file that matches their domain, or a new `*.yml` file.
2. Edit the entry. Minimal shape:

   ```yaml
   my-service:
     description: "What it does"
     groups: ["base", "internal"]
   ```

3. Validate: `python3 scripts/validate-config.py` (activate the venv first if present).
4. Preview: `make plan` (all repos) or `make plan-repo REPO=my-service` (single repo,
   uses `terraform plan -target`).
5. Review the plan before `make apply` — see the `plan-safety-review` skill for what to
   flag. Never apply a plan that destroys or flips visibility without explicit confirmation.

## Group merge semantics

- `groups` is an ordered list; group definitions live in `config/group/*.yml`.
- Later groups override earlier ones for scalar settings; list values (e.g. `topics`,
  `rulesets`) are merged.
- Repository-level settings override everything from groups.
- Global defaults come from `config/config.yml`.

## Tier gating

`subscription` in `config/config.yml` (`free` | `pro` | `team` | `enterprise`) gates features:

- `free`: rulesets only on public repos (private-repo rulesets are skipped with a warning)
- `free`/`pro`: organization-scoped rulesets skipped (`skipped_org_rulesets` output)
- `team`/`enterprise`: full ruleset and security-manager support

The validator warns on tier conflicts; do not "fix" a skip warning by changing the tier
unless the user actually has that subscription.

## Removing a repository

Deleting the YAML entry makes Terraform plan a **destroy** of the live repository on the
next apply. If the repo should keep existing on GitHub unmanaged, use the offboard flow
(`onboard-offboard` skill) to remove it from state first.

## Provider attribute lookups

When unsure how a `github_*` resource attribute behaves for the pinned provider version
(`integrations/github >= 6.12, < 7.0`), prefer the Terraform Registry MCP server (declared
in `.mcp.json`) to fetch the exact provider docs; otherwise consult
<https://registry.terraform.io/providers/integrations/github/latest/docs> directly.
