# GitHub As YAML: Project Research Document

> **Date:** 2026-02-25
> **Status:** Draft
> **Scope:** Architecture analysis, strengths, weaknesses, competitive landscape

______________________________________________________________________

## Table of Contents

- [Executive Summary](#executive-summary)
- [What This Project Does](#what-this-project-does)
- [Architecture Overview](#architecture-overview)
- [Competitive Landscape](#competitive-landscape)
- [Strengths (Pros)](#strengths-pros)
- [Weaknesses (Cons)](#weaknesses-cons)
- [Gaps and Missing Features](#gaps-and-missing-features)
- [Risks](#risks)
- [Recommendations](#recommendations)

______________________________________________________________________

## Executive Summary

**GitHub As YAML** is a Terraform project that lets you manage GitHub
organization repositories entirely through YAML configuration files. Instead of
writing HCL for each repository, you declare repos, groups, rulesets, and
webhooks in YAML — Terraform reads and applies them.

The project works both as a **standalone setup** (clone and use directly) and as
a **reusable Terraform module** that consumers import into their own Terraform
root. It manages repositories, team permissions, collaborators, branch rulesets,
GitHub Actions permissions, and webhooks.

The core value proposition is: **day-to-day GitHub org management should not
require Terraform expertise.** A developer who can edit YAML can add a repo,
assign teams, and configure branch protection.

______________________________________________________________________

## What This Project Does

### Resources Managed

| Resource            | Terraform Resource                        | Config Source                       |
| ------------------- | ----------------------------------------- | ----------------------------------- |
| Repositories        | `github_repository`                       | `config/repository/*.yml`           |
| Team access         | `github_team_repository`                  | Groups or per-repo `teams:`         |
| Collaborators       | `github_repository_collaborator`          | Groups or per-repo `collaborators:` |
| Branch/tag rulesets | `github_repository_ruleset`               | `config/ruleset/*.yml` + references |
| Actions permissions | `github_actions_repository_permissions`   | Groups or per-repo `actions:`       |
| Org Actions policy  | `github_actions_organization_permissions` | `config/config.yml` `actions:`      |
| Webhooks            | `github_repository_webhook`               | `config/webhook/*.yml` + references |

### Configuration Hierarchy

```text
config.yml (org-level defaults)
    └── groups (merged left-to-right)
         └── per-repository overrides
```

- **Scalars** (visibility, has_wiki): later value wins
- **Lists** (topics, action patterns): merged and deduplicated
- **Maps** (teams, collaborators): merged (keys from all sources)
- **Rulesets**: concatenated from all groups + repo-level

### Two Usage Modes

1. **Direct:** Clone the repo, edit `config/`, run `make plan && make apply`
1. **Module consumer:** Import `terraform/` as a module, point `config_path` at
   your own YAML directory, configure your own provider and backend

______________________________________________________________________

## Architecture Overview

### Data Flow

```text
config/config.yml           ─┐
config/group/*.yml           ├─→  yaml-config.tf   ─→  local.repositories  ─→  module.repositories
config/repository/*.yml      │    (638 lines of        (for_each)              (per-repo resources)
config/ruleset/*.yml         │     merge logic)
config/webhook/*.yml        ─┘
```

### Key Design Decisions

1. **YAML parsed at plan time** via `file()` + `yamldecode()` — no external
   data sources, no generators, no preprocessing step.

1. **Directory-based config splitting** — each config type lives in its own
   directory (`config/group/`, `config/repository/`, etc.), allowing multiple
   YAML files per type. Files are merged alphabetically.

1. **Group-based composition** — repositories reference named groups. Groups
   define shared settings. This avoids repetition across dozens of repos with
   similar configurations.

1. **Ruleset templates** — reusable ruleset skeletons with override support.
   Reference as `{template: "strict-main", enforcement: "evaluate"}` to use
   a template with modifications.

1. **No provider block in module** — consumers must configure the GitHub
   provider themselves. This keeps the module cloud-agnostic in its provider
   management.

1. **Subscription-aware filtering** — rulesets for private repos on the free
   GitHub tier are automatically skipped (with warnings), preventing plan
   errors.

### File Inventory (Key Files)

| File                                        | Lines | Purpose                                                     |
| ------------------------------------------- | ----- | ----------------------------------------------------------- |
| `terraform/yaml-config.tf`                  | 638   | Heart of the system — all YAML parsing, merging, validation |
| `terraform/main.tf`                         | 100   | Entry point, module call, org-level Actions resources       |
| `terraform/modules/repository/main.tf`      | 229   | All per-repo resource definitions                           |
| `terraform/modules/repository/variables.tf` | 212   | Full type definitions for module inputs                     |
| `scripts/validate-config.py`                | 291   | Pre-commit YAML validation                                  |
| `scripts/onboard-repos.sh`                  | 379   | Import existing GitHub repos into Terraform                 |
| `scripts/offboard-repos.sh`                 | 299   | Remove repos from Terraform state                           |
| `scripts/migrate-state.sh`                  | 176   | Migrate state for module adoption                           |

______________________________________________________________________

## Competitive Landscape

A GitHub search for similar projects reveals a **very sparse landscape**:

| Project                                                                                         | Stars | Approach                                           | Status                               |
| ----------------------------------------------------------------------------------------------- | ----- | -------------------------------------------------- | ------------------------------------ |
| [xebis/github-organization-as-code](https://github.com/xebis/github-organization-as-code)       | 0     | Terraform + YAML + GitHub Actions + AWS S3 backend | Active, low adoption                 |
| [alexjuda/github-as-code](https://github.com/alexjuda/github-as-code)                           | 0     | "Terraform for GitHub configs"                     | Minimal, unclear scope               |
| [vincishq/terraform-module-github](https://github.com/vincishq/terraform-module-github)         | 0     | "Module for managing GitHub config in code"        | Minimal                              |
| [masterpointio/terraform-github-teams](https://github.com/masterpointio/terraform-github-teams) | 10    | Terraform module for GitHub teams only             | Active, narrow scope                 |
| [HariSekhon/Terraform](https://github.com/HariSekhon/Terraform)                                 | 55    | Multi-cloud Terraform (AWS/GCP/Azure/GitHub)       | Active, but GitHub is a side concern |

### Key Observations

- **No established player** exists in this space with meaningful adoption.
- Most projects are either too narrow (teams only) or too broad (multi-cloud).
- The `xebis/github-organization-as-code` project is the closest competitor —
  same concept, same creation month (Feb 2025) — but has zero traction.
- The broader Terraform ecosystem has `terraform-provider-github` but no
  widely-adopted opinionated wrapper for YAML-driven config.

### Differentiation

GitHub As YAML's differentiators versus the field:

1. **Reusable module pattern** — works as both standalone and importable module
1. **Group composition system** — no competitor has this
1. **Ruleset templates with overrides** — unique feature
1. **Subscription-aware filtering** — handles free tier gracefully
1. **Operational scripts** — onboard, offboard, migrate tooling
1. **Spec-driven development** (OpenSpec) — unusual rigor for this project size

______________________________________________________________________

## Strengths (Pros)

### 1. Zero HCL Required for Day-to-Day Operations

The entire point of the project works: you edit YAML, run `terraform apply`,
and repositories appear with the right settings. A junior developer or a
non-infrastructure engineer can manage the GitHub org without learning HCL.

### 2. Group Composition is Genuinely Useful

The ability to define groups like `oss` and `internal` with shared settings,
then assign `groups: ["base", "oss"]` to a repo, eliminates massive
duplication. The merge semantics (scalars override, lists merge, maps merge)
are well-thought-out and handle real-world cases.

### 3. Clean Module Boundary

The separation between `terraform/` (the module) and `config/` (user data)
is clean. The module exposes exactly two variables (`config_path` and
`webhook_secrets`), which is a very tight interface. Consumers can wrap it
without touching internals.

### 4. Ruleset Templates with Overrides

The template system (`template: "strict-main"` with inline overrides) solves
a real problem: you want 90% of a ruleset but need to tweak enforcement or
approval count. This avoids copy-pasting entire ruleset definitions.

### 5. Subscription-Aware Behavior

Automatically skipping rulesets that won't work on the free tier (with
warnings) is a thoughtful touch. Most Terraform projects just let you apply
invalid config and get API errors.

### 6. Comprehensive Operational Scripts

The `onboard-repos.sh`, `offboard-repos.sh`, and `migrate-state.sh` scripts
address real adoption pain points. Importing 50 existing repos into Terraform
is tedious; these scripts automate it.

### 7. Thorough Pre-commit Validation

The pre-commit pipeline catches issues early: Terraform fmt/validate/tflint,
YAML lint, markdown lint, secret detection, and custom config validation.
This is more thorough than most projects 10x its size.

### 8. Spec-Driven Development (OpenSpec)

The `openspec/` directory with formal specs, change proposals, and an archive
provides unusual discipline. This makes the project's design decisions
traceable and reviewable.

### 9. Multi-File Config Support

Splitting repositories across multiple YAML files (`config/repository/*.yml`)
means teams can own their own files, reducing merge conflicts. Same applies
to groups and rulesets.

### 10. Duplicate Key Detection

The `duplicate_key_warnings` output catches when the same repo/group/ruleset
name appears in multiple files — a subtle bug that YAML's `merge()` would
silently resolve by last-write-wins.

______________________________________________________________________

## Weaknesses (Cons)

### 1. `yaml-config.tf` is a 638-Line Monster

All YAML parsing, group merging, ruleset template resolution, actions config
merging, webhook resolution, subscription filtering, and validation lives in
a single file. This is the most complex file in the project and the hardest
to understand, debug, or extend.

The merge logic for actions alone (lines 234-436) spans 200 lines of deeply
nested `coalesce()` and `lookup()` calls. A bug here affects every repository.

**Impact:** High maintenance burden. New contributors will struggle to
understand or safely modify this file.

### 2. `config.yml` Defaults Block is Dead Code

The `defaults:` block in `config/config.yml` (lines 19-32) is defined and
documented but **never consumed by Terraform**. The actual defaults are
hardcoded as fallback values in `yaml-config.tf`'s `lookup()` calls.

This is misleading — a user edits `defaults.visibility: public` expecting it
to work, but nothing changes. The defaults are baked into HCL.

**Impact:** User confusion, false sense of configurability.

### 3. No CI/CD Pipeline

Despite having a `plan-pr` Makefile target and a `tfcmt` reference, there are
no GitHub Actions workflows. For a project that manages GitHub infrastructure,
having no automated plan-on-PR workflow is a significant gap — especially for
the "module consumer" use case where you'd want to ship a ready-to-use CI
template.

**Impact:** Users must build their own CI from scratch. Reduces the "template"
value proposition.

### 4. Merge Semantics Are Implicit and Undocumented

The rules for how groups merge (scalars: last wins; lists: concat+dedup; maps:
merge) are buried in `yaml-config.tf`. There is no user-facing documentation
that explains: "If group A sets `visibility: public` and group B sets
`visibility: private`, which wins?"

The answer is: the last group in the `groups:` array wins for scalars. But
this is non-obvious and could cause accidental public exposure.

**Impact:** Risk of misconfiguration. Visibility changes (private to public)
are particularly dangerous.

### 5. No Drift Detection or Plan Output in Config Validation

The `validate-config.py` script checks YAML structure but cannot detect:

- A repo that exists in GitHub but not in config (orphaned)
- A repo in config that was manually modified in GitHub (drift)
- Rulesets that reference non-existent teams or users

These are runtime concerns that only `terraform plan` catches, but
`validate-config.py` gives users a false sense of completeness.

**Impact:** Users may trust validation output and skip `terraform plan` review.

### 6. No State Backend Configuration

The root `terraform/` directory has no backend configuration. The
`examples/consumer/` provides templates but the main project defaults to
local state. For a tool managing org-wide GitHub settings, local state is
dangerous — no locking, no team collaboration, no recovery.

**Impact:** Data loss risk, state conflicts in team usage.

### 7. The `--strict` Flag in validate-config.py is a No-Op

The script accepts `--strict` but it doesn't change behavior. This is either
incomplete implementation or dead code.

**Impact:** Minor, but erodes trust in the tooling.

### 8. Webhook Secret Pattern is Misleading

Webhook secrets use the pattern `env:VAR_NAME` which suggests environment
variable resolution. In reality, it resolves against `var.webhook_secrets`
(a Terraform variable map). The naming creates a false mental model.

**Impact:** User confusion during webhook setup.

### 9. No Import/Adoption Path for Rulesets, Teams, or Webhooks

The `onboard-repos.sh` script imports repositories but not their rulesets,
team assignments, or webhooks. After import, the first `terraform apply`
will either create duplicate rulesets or fail on conflicts.

**Impact:** Incomplete migration story for existing orgs with branch
protection already configured.

### 10. `wt-template/` is Confusing Cruft

The `wt-template/` directory is a stale git worktree containing an older
snapshot of the project. It has its own `.git` file and diverged state.
Its purpose is undocumented and it inflates the repo size.

**Impact:** Confuses contributors, inflates clone size.

### 11. Wiki Submodule Adds Friction

The wiki is a git submodule (`wiki/`). Submodules are notoriously painful —
they don't clone by default, require `--recurse-submodules`, and break
shallow clones. For a template repo that users fork, this is friction.

**Impact:** Poor first-experience for users who clone/fork.

______________________________________________________________________

## Gaps and Missing Features

### Not Yet Implemented

| Feature                                                 | Complexity | Value  |
| ------------------------------------------------------- | ---------- | ------ |
| GitHub Actions CI workflow (plan on PR)                 | Low        | High   |
| Consuming `config.yml` defaults in Terraform            | Low        | Medium |
| GitHub Actions workflow templates for consumers         | Medium     | High   |
| Environment/deployment management                       | Medium     | Medium |
| Branch default settings (default branch name)           | Low        | Low    |
| Repository template support (`is_template`, `template`) | Low        | Medium |
| Dependabot/Renovate config management                   | High       | Medium |
| File provisioning (CODEOWNERS, LICENSE, etc.)           | High       | High   |
| Repository archival workflow                            | Low        | Medium |
| Custom properties / repository topics from org level    | Medium     | Low    |

### Proposed but Not Shipped (Active OpenSpec Changes)

1. **`add-dependabot-renovate-config`** — Managing Dependabot/Renovate config
   files across repos. Depends on file provisioning.

1. **`add-file-provisioning-workflow`** — Provisioning files (CODEOWNERS,
   .github/ templates) to repos via branch-based workflow to work around
   Terraform's unsigned commits issue.

1. **`add-ruleset-templates`** — Partially implemented. The template system
   exists in code but the proposal hasn't been archived, suggesting it may
   be incomplete.

______________________________________________________________________

## Risks

### 1. Visibility Escalation

The group merge system means adding a group to a repo can silently change its
visibility from `private` to `public`. There is no confirmation gate, no
separate approval requirement, and no Terraform `prevent_destroy`-style
guard for visibility changes.

**Mitigation:** Add a `check` block or validation that flags visibility
changes, or require explicit `visibility:` on every repo definition.

### 2. Single Point of Complexity

`yaml-config.tf` is the single point of failure. A bug in the merge logic
affects every repository. The file has no unit tests — correctness relies
entirely on `terraform plan` review.

**Mitigation:** Extract merge logic into a tested helper (though Terraform's
testing capabilities are limited), or add comprehensive plan-output tests.

### 3. State Corruption on Module Path Changes

If a consumer changes their module call (e.g., renames from `module.github`
to `module.github_org`), all state addresses change. The `migrate-state.sh`
script helps but is manual and error-prone.

**Mitigation:** Document the module path as a permanent decision. Consider
adding state migration to CI.

### 4. Provider Version Sensitivity

The lock file pins `integrations/github` at `6.10.1`. The GitHub provider
has historically introduced breaking changes. The module has no version
compatibility matrix or tested range.

**Mitigation:** Document tested provider versions. Add CI that tests against
multiple provider versions.

______________________________________________________________________

## Recommendations

### Quick Wins (Low Effort, High Value)

1. **Wire up `config.yml` defaults** — The `defaults:` block exists in config
   but is ignored by Terraform. Either consume it or remove it.

1. **Add a GitHub Actions workflow** — Even a minimal plan-on-PR workflow would
   dramatically increase the template's value.

1. **Document merge semantics** — A table showing "scalars: last group wins,
   lists: merged, maps: merged" with examples would prevent misconfig.

1. **Remove `wt-template/`** — It's stale cruft that confuses contributors.

1. **Archive the `add-ruleset-templates` change** — The feature is implemented.

### Medium-Term Improvements

6. **Split `yaml-config.tf`** — Break into `yaml-parsing.tf`,
   `group-merging.tf`, `ruleset-resolution.tf`, `actions-config.tf` for
   maintainability.

1. **Add visibility change guards** — A `check` block or precondition that
   warns when a repo's visibility would change.

1. **Ship a consumer CI template** — A ready-to-use GitHub Actions workflow
   in `examples/consumer/.github/workflows/`.

1. **Implement `--strict` mode** — Make it enforce additional rules
   (e.g., every repo must have explicit `visibility:`, no empty descriptions).

### Strategic Considerations

10. **Name:** Rebranded to `github-as-yaml` — short, descriptive, and
    communicates the YAML-driven approach immediately.

01. **Adoption path:** The biggest barrier isn't features — it's that nobody
    knows this exists. A clear README with a 30-second quickstart, a blog
    post, and Terraform Registry publishing would do more for adoption than
    any feature work.

01. **Testing:** Terraform testing (`terraform test`) could validate the
    merge logic with synthetic YAML configs. This is the highest-risk
    untested area.

______________________________________________________________________

## Conclusion

GitHub As YAML is a well-designed project solving a real problem in an empty competitive
space. The core architecture — YAML config parsed into Terraform module
instances via a merging layer — is sound. The group composition system and
ruleset templates are genuine differentiators.

The main weaknesses are operational: no CI pipeline, undocumented merge
semantics, dead config code, and a 638-line merge file that's hard to
maintain. None of these are architectural flaws — they're polish and
documentation gaps that are straightforward to fix.

The competitive landscape is effectively empty. No project in this space has
meaningful adoption. This is both an opportunity (first-mover advantage) and a
warning (maybe the market doesn't want this). The strongest argument for
demand is that nearly every GitHub organization eventually builds something
like this internally — GitHub As YAML could be the thing they reach for instead.
