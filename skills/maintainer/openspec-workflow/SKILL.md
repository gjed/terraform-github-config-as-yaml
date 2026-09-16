---
name: openspec-workflow
description: >-
  Follow the mandatory openspec change process for the terraform-github-config-as-yaml
  repository. MAINTAINER-ONLY — does not apply to module consumers. Use before planning any
  feature, behavior change, or spec work in this repo; when creating, updating, implementing, or
  archiving a change proposal; or when writing spec-related commits. Triggers on "propose a
  change", "new feature", "update the spec", "archive the change".
---

# Openspec workflow (maintainer only)

Openspec is a **mandatory gating process** in this repository: features and behavior changes are
specified in `openspec/` before implementation. Do not improvise planning documents or skip
straight to code for spec-worthy work.

## Layout

- `openspec/specs/<capability>/spec.md` — current, authoritative specs.
- `openspec/changes/<change-id>/` — active change proposals: `proposal.md`, `tasks.md`,
  optional `design.md`, and delta specs under `specs/`.
- `openspec/changes/archive/<date>-<change-id>/` — completed changes.
- `openspec/config.yaml` — project context given to spec tooling.

## Lifecycle

1. **Propose** — create `openspec/changes/<change-id>/` with proposal, tasks, and delta specs
   (project skill: `openspec-propose`).
2. **Implement** — work through `tasks.md`, checking items off (`openspec-apply-change`).
3. **Sync/Archive** — merge delta specs into `openspec/specs/` and move the change to
   `archive/` with a date prefix (`openspec-sync-specs`, `openspec-archive-change`).

Bug fixes with spec impact get a change too (see archived `fix-*` changes for the pattern);
trivial chores do not.

## Commit conventions

Conventional Commits, spec-specific types:

- `feat(spec): add <name>` — new spec or change proposal.
- `refactor(spec): update <name>` — updating a spec or proposal.
- `chore(spec): archive <name>` — archiving a completed change.

## Rules

- What counts as spec-worthy: anything changing module behavior, interfaces, or consumer
  contract. Docs/tooling-only changes usually are not — ask if unclear.
- Delta specs must use the requirement/scenario format of the existing specs — copy structure
  from a recent change in `archive/`.
- Run the markdown gate after editing:
  `pre-commit run --all-files` (markdownlint excludes `.opencode/`, not `openspec/`).
- Never edit `openspec/specs/` directly for new work — changes flow through a change proposal.
