---
name: onboard-offboard
description: >-
  Bring existing GitHub repositories under Terraform management, or remove repositories from
  management without deleting them. Use when importing pre-existing repos into state, generating
  YAML for repos that already exist on GitHub, offboarding archived repos, listing managed vs
  unmanaged repos, or migrating state paths after adopting the published module. Triggers on
  "import repo", "onboard", "offboard", "stop managing", "terraform state mv/rm", or
  "state migration".
---

# Onboard and offboard repositories

Three shipped scripts cover the lifecycle. All support `--dry-run`; always dry-run first and
show the user the output before executing state-changing commands.

## Onboarding (`scripts/onboard-repos.sh`)

Requires `gh` CLI authenticated and `terraform init` done.

```bash
# Discover what exists in the org
./scripts/onboard-repos.sh --list [--filter "api-"]

# Generate YAML entries (review/merge into config/repository/ before importing)
./scripts/onboard-repos.sh --generate-yaml repo1 repo2

# Import into Terraform state
./scripts/onboard-repos.sh --import repo1 repo2

# Both at once
./scripts/onboard-repos.sh --generate-yaml --import repo1 repo2
```

When the module is consumed from a wrapper root (the published-module layout), resource
addresses are nested — pass `--module-path "module.github_org."` (match the consumer's module
block name). Without it, imports target the wrong address and fail.

After importing: run `terraform plan`. A clean onboard shows no changes, or only deliberate
normalization. Unexpected diffs mean the generated YAML does not match live settings — fix the
YAML, not GitHub.

## Offboarding (`scripts/offboard-repos.sh`)

Removes repos from Terraform state **without deleting them on GitHub** — the correct move for
archived repos or repos leaving management.

```bash
./scripts/offboard-repos.sh --list                          # what is currently managed
./scripts/offboard-repos.sh --dry-run repo1 repo2           # preview
./scripts/offboard-repos.sh --remove-config repo1 repo2     # state + YAML cleanup
```

Same `--module-path` rule applies. Never offboard by deleting the YAML entry alone: with the
entry gone, the next apply **destroys the repository on GitHub**. State removal must come first.

## State migration (`scripts/migrate-state.sh`)

For forks adopting the published module, state paths move from
`module.repositories[...]` to `module.github_org.module.repositories[...]`:

```bash
./scripts/migrate-state.sh                 # dry-run: prints terraform state mv commands
./scripts/migrate-state.sh --execute       # perform the migration
```

Use `--target-prefix "module.<name>."` when the consumer's module block is not `github_org`.
Back up state before executing (`terraform state pull > backup.tfstate`).

## Pre-import inspection (optional MCP)

If a read-only GitHub MCP server (`github` in the repo's `.mcp.json`) is available, use it to
verify a repository exists and inspect its live settings (visibility, default branch, topics)
before generating YAML — cheaper and more precise than a full plan. All changes still go
through YAML + Terraform.
