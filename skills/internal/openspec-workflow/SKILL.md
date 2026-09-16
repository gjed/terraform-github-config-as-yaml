---
name: openspec-workflow
description: >-
  Follow this repository's mandatory openspec process for planning and spec work.
  Maintainer-only. Use before implementing any feature, behavior change, or removal; when
  creating change proposals; when archiving shipped changes; or when editing anything under
  openspec/.
---

# Openspec workflow (maintainers)

Openspec is a **mandatory gate**: features, behavior changes, and removals get a change
proposal before implementation. Pure chores (lint fixes, dependency bumps) do not.

## Layout

- `openspec/specs/<capability>/spec.md` — current truth, one spec per capability
- `openspec/changes/<change-id>/` — active proposals: `proposal.md`, `tasks.md`, optional
  `design.md`, and `specs/<capability>/spec.md` deltas
- `openspec/changes/archive/YYYY-MM-DD-<change-id>/` — shipped changes

## Change lifecycle

1. Create `openspec/changes/<change-id>/` with `proposal.md` (Why / What Changes /
   Capabilities / Impact) and `tasks.md` (numbered checklist).
2. Spec deltas use `## ADDED|MODIFIED|REMOVED|RENAMED Requirements` headers; every
   requirement needs at least one `#### Scenario:` block. A MODIFIED block replaces the whole
   requirement — copy scenarios you keep, or validation fails.
3. Validate: `openspec validate <change-id> --strict` (venv: `source .venv/bin/activate`).
4. Implement, ticking `tasks.md` items (`- [x]`).
5. After shipping, archive: `openspec archive <change-id> --yes` — this applies the deltas to
   `openspec/specs/` and moves the change dir into `archive/`.

## Commit conventions

- `feat(spec): add <change-id>` — new proposal
- `refactor(spec): update <change-id>` — amend a pending proposal
- `chore(spec): archive <change-id>` — archive after shipping
- Implementation commits are ordinary conventional commits; breaking module-interface
  changes use `!` plus a `BREAKING CHANGE:` footer (drives semantic-release major bumps).

## Rules

- Do not edit `openspec/specs/` by hand — specs change only via archived deltas.
- Do not edit anything under `openspec/changes/archive/` — it is historical record.
- `openspec list` shows active changes and task progress.
- Run `pre-commit run --all-files` after markdown edits; specs are markdownlint-checked
  (120-column lines).
