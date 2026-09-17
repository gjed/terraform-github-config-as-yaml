---
name: onboard-offboard
description: >-
  Bring existing GitHub repositories under Terraform management, or release repositories from
  management without deleting them. Use when the user asks to "import existing repos", "onboard
  repo X", "stop managing repo Y", or needs Terraform state surgery for this module
  (state mv/rm after refactors).
---

# Onboard / offboard repositories

Three shipped scripts. All support `--dry-run`; use it first, always. For wrapped consumers
(module call like `module "github_org"`), pass `--module-path "module.github_org."`.

## Onboard (import existing repos)

`scripts/onboard-repos.sh` discovers repos on GitHub, generates YAML, and imports state:

```bash
./scripts/onboard-repos.sh --list                       # list org repos (add -f PATTERN to filter)
./scripts/onboard-repos.sh -y my-repo other-repo        # generate YAML entries (print to stdout)
./scripts/onboard-repos.sh -i -g base,internal my-repo  # import into Terraform state
./scripts/onboard-repos.sh -d -i my-repo                # dry-run of the import
```

Order matters: the YAML entry must exist in `config/repository/` **before** importing —
`terraform import` refuses addresses that do not exist in configuration, and the entry is
what creates the `module.repositories["<name>"]` instance to import into.

After importing, run `make plan` — the goal is an **empty diff** (or only benign updates).
A non-empty diff means the YAML does not match the live repo; fix the YAML, not GitHub.

## Offboard (stop managing, keep the repo)

`scripts/offboard-repos.sh` removes repos from Terraform state so they keep existing on
GitHub unmanaged:

```bash
./scripts/offboard-repos.sh --list              # what is currently in state
./scripts/offboard-repos.sh -d my-repo          # dry-run
./scripts/offboard-repos.sh -c my-repo          # state rm + remove YAML entry
```

Never offboard by just deleting the YAML entry — that plans a **destroy** of the live
repository. State removal must happen first (the script does it in the right order).

## State migration

`scripts/migrate-state.sh` helps move resource addresses after refactors (e.g. flat →
wrapped module layout). Dry-run first, and back up state (`terraform state pull > backup.tfstate`)
before any `state mv`/`state rm` session.

## Verification

Every onboard/offboard session ends with `make plan` and a review via the
`plan-safety-review` skill. The read-only GitHub MCP server from `.mcp.json` (or `gh repo view`)
is useful to inspect a repo's live settings before writing its YAML entry.
