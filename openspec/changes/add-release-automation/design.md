## Context

Releasing has been fully manual since `1.0.1` (2026-03-06). 74 commits have landed on `main`
since, none released. The tag history itself shows the manual process was inconsistent: `1.0.0`
and `v1.0.0` both point at the same commit, `1.0.1` is unprefixed.

Two facts about this repository constrain the design and were verified directly against the
GitHub API before writing this proposal, not assumed:

- `main` carries two active branch rulesets. `gjed-oss-main` requires `required_signatures`,
  `pull_request` (1 approval, code-owner review), `required_linear_history`, `non_fast_forward`.
  `oss-main-protection` overlaps it with a weaker PR requirement. Both target `branch`, not `tag`.
- The Terraform module has no in-tree version file. There is nothing for a tool to bump inside
  the repository — the version lives entirely in the tag.

## Goals / Non-Goals

**Goals:** merging conventional commits to `main` produces a correctly-versioned tag and GitHub
Release automatically; the Terraform Registry picks it up without further action.

**Non-Goals:** an in-repo `CHANGELOG.md`. Not attempting one — see Decision 2.

## Decisions

### Decision 1: `tagFormat: "v${version}"`, with the existing tags backfilled

Going forward the repository standardizes on `v`-prefixed tags. The existing published tags are
unprefixed (`1.0.0`, `1.0.1`), so they must be backfilled as `v1.0.0` and `v1.0.1` on the same
commits before the workflow is enabled.

This backfill is a prerequisite, not a cleanup task. semantic-release filters tags by `tagFormat`
when determining the last release — an unmatched tag is invisible to it, not merely deprioritized.
With `tagFormat: "v${version}"` and no `v`-prefixed tag present, the tool would find no prior
release at all and publish `v1.0.0` as an initial release instead of `v1.1.0`.

The unprefixed tags are kept, not deleted. The Terraform Registry has published `1.0.0` and
`1.0.1` from them, and consumers may pin those versions; deleting the tags they resolve from is
destructive. Both naming schemes therefore coexist for the two historical releases, and only
`v`-prefixed tags are created from here on.

### Decision 2: No `@semantic-release/git`, no `@semantic-release/changelog`

`@semantic-release/git` commits an updated `CHANGELOG.md` back to the release branch. On this
repo that commit would need to land on `main`, which requires a signed commit made through an
approved pull request. A GitHub Actions bot commit satisfies neither. This is not a corner case —
it is the same signed-commit constraint already tracked in issue #51 for the file-provisioning
workflow. Excluding these plugins avoids building a workflow that fails on its first run.

Release notes still exist — `@semantic-release/github` publishes them to the GitHub Release
itself, which is not subject to branch protection.

### Decision 3: explicit `conventionalcommits` preset, not the plugin default

`@semantic-release/commit-analyzer` and `@semantic-release/release-notes-generator` default to the
`angular` preset. That preset's header regex does not capture `!` — only a `BREAKING CHANGE:`
footer triggers a major bump. This repo's `CONTRIBUTING.md` documents `feat!: breaking change` as
a valid marker. Left on defaults, a commit written exactly as the repo's own docs instruct would
silently release as a minor bump instead of major. Both plugins are configured with
`preset: "conventionalcommits"` to close that gap.

### Decision 4: trigger on `push: branches: [main]`, not `on: release` or tag push

The tag is an output of the release, not a trigger for it — there is no prior tag to react to
before the first automated release exists. `fetch-depth: 0` is required because semantic-release
walks full tag history to find the last release; a shallow checkout would see no prior tags at all
and treat every run as the first release.

### Decision 5: `cycjimmy/semantic-release-action`, not a root `package.json`

This repository has no other Node.js usage — no `package.json`, no `node_modules` anywhere. Adding
one solely to run `npx semantic-release` introduces an npm dependency tree, a lockfile, and Node
version management (`.nvmrc` or similar) for a tool that runs once per merge. The Action bundles
its own Node runtime and takes plugin list + config via `.releaserc.json`, which is the pattern
this repo already uses for `pre-commit` (declarative config file, tool provided by the CI runner).

## First-Run Version Decision

74 unreleased commits include no `!`-marked or `BREAKING CHANGE:`-footer commit, so the first
automated run computes `1.1.0`. One of those commits, `9aec9a4`, migrated `vulnerability_alerts`
from a `github_repository` argument to a standalone
`github_repository_vulnerability_alerts` resource — a state-changing behavior for existing
consumers on next `terraform apply`, arguably major, but it was committed as `fix:` before this
proposal existed and won't be reclassified retroactively.

This is a human call, made once, outside the scope of automation: accept `1.1.0` with the state
change called out in release notes, or hand-tag `2.0.0` before turning the workflow on. Recorded
in tasks.md as an explicit step rather than decided here.

## Risks

- **First release scope.** 74 commits landing as a single `1.1.0` release is a large diff for one
  version bump. Not a design flaw — future releases will be much smaller since they fire per
  merge going forward.
- **Registry lag.** The Registry has historically synced within roughly a minute of tag push; if
  it doesn't, the fallback is triggering "Resync Module" in the Registry UI. No API-level retry is
  built into this proposal since the Registry does not expose one.
