## Why

Releases are entirely manual, and the module has drifted badly out of sync with `main` as a result.

The last release, `1.0.1`, was tagged 2026-03-06. Since then **74 commits** have landed on
`origin/main` — teams management, repository partitioning, org membership, branch protection,
org rulesets, org webhooks, org settings, security manager teams, the e2e test fixture, and the
`vulnerability_alerts` migration. None of it has been released. The Terraform Registry still
serves only `1.0.0` and `1.0.1`, so no consumer pinning `~> 1.0` has received any of that work.

The manual process has also produced inconsistent tags. `origin` carries only unprefixed tags
(`1.0.0`, `1.0.1`), while both GitHub Releases are *titled* with a `v` prefix (`v1.0.0`,
`v1.0.1`) — the prefix exists in the release names but never in the refs. Nothing enforces a
single convention.

The repository already requires Conventional Commits (`CONTRIBUTING.md`), so the version bump is
already derivable from history — it is simply never computed.

## What Changes

- **NEW**: `.releaserc.json` — semantic-release configuration with `tagFormat: "v${version}"`,
  standardizing on `v`-prefixed tags
- **BACKFILL**: `v1.0.0` and `v1.0.1` tags created on the existing release commits (`e6b4cc9`,
  `4b1e2a1`). Required before enabling the workflow — semantic-release only resolves the last
  release from tags matching `tagFormat`, so without these it would publish an initial `v1.0.0`
  instead of `v1.1.0`. The unprefixed tags are retained because the Registry's published `1.0.0`
  and `1.0.1` versions resolve from them.
- **NEW**: `.github/workflows/release.yml` — runs semantic-release on every push to `main`,
  computing the version, creating the git tag, and publishing a GitHub Release with generated
  notes
- **REMOVED**: the manual tag-and-release step. Releasing is no longer a human action; there is
  no tag-triggered workflow, because the tag is an output of the release rather than its trigger
- **BREAKING**: None for module consumers. This changes how the repository is released, not what
  it does.

## Capabilities

### New Capabilities

- `release-automation`: derive the next semantic version from Conventional Commit history on
  `main`, tag it, and publish a GitHub Release with generated notes, without human intervention

## Impact

- Affected specs: new `release-automation` capability
- Affected code:
  - `.releaserc.json` (new)
  - `.github/workflows/release.yml` (new — this is the repository's first workflow)
  - `CONTRIBUTING.md` — document that merges to `main` release automatically, and that commit
    type therefore determines the version bump
- Affected refs: `v1.0.0` and `v1.0.1` tags backfilled on `origin` (no existing ref is deleted or
  moved)

## Constraints

Two properties of this repository dictate the design and are not negotiable:

1. **`main` requires signed commits.** Ruleset `gjed-oss-main` (active) enforces
   `required_signatures`, `pull_request` with 1 approval and code-owner review, plus
   `required_linear_history` and `non_fast_forward`. A second ruleset, `oss-main-protection`,
   overlaps it. Consequently semantic-release **cannot commit anything back to `main`** — this is
   the same unsigned-commit problem tracked in #51 for file provisioning. `@semantic-release/git`
   and `@semantic-release/changelog` are therefore excluded by design, not by preference.

2. **Neither ruleset targets tags.** Both are `target: branch`, so creating a release tag is
   unobstructed.

## First-Run Consideration

The first automated run will evaluate all 74 commits since `1.0.1`. Those include `feat:` commits
but no commit marked `!` or carrying a `BREAKING CHANGE:` footer, so semantic-release will compute
**`1.1.0`**.

That deserves an explicit decision before the first run. Commit `9aec9a4` migrated
`vulnerability_alerts` from a `github_repository` argument to a standalone
`github_repository_vulnerability_alerts` resource. For an existing consumer that is a state
change on next apply, not a no-op — arguably a major bump. It was committed as `fix:`, so
automation will not treat it as breaking.

**Decision: accept `v1.1.0`.** The state change is called out in the release notes rather than
escalated to a major bump.
