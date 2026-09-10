## ADDED Requirements

### Requirement: Automated Semantic Versioning

The system SHALL derive the next release version from Conventional Commit history rather than from
a human-chosen tag. Releasing SHALL require no manual action beyond merging to the default branch.

Version bumps SHALL follow the `conventionalcommits` preset mapping: `feat` produces a minor
bump, `fix` and `perf` produce a patch bump, and either a `!` marker after the type or a
`BREAKING CHANGE:` footer produces a major bump. Commit types that describe no user-visible change
SHALL NOT produce a release on their own.

`@semantic-release/commit-analyzer`'s built-in default preset is `angular`, whose header pattern
does not capture `!` — only the `BREAKING CHANGE:` footer triggers a major bump under that preset.
This repository's `CONTRIBUTING.md` documents `!` as a valid breaking-change marker
(`feat!: breaking change`). To honor that convention, both `commit-analyzer` and
`release-notes-generator` SHALL be explicitly configured with `preset: "conventionalcommits"`
rather than left on their `angular` default.

#### Scenario: Feature merge produces a minor release

- **GIVEN** the last release is `1.0.1`
- **AND** a commit `feat(webhooks): add organization webhook support` is merged to `main`
- **WHEN** the release workflow runs
- **THEN** version `1.1.0` is computed
- **AND** the tag `1.1.0` is created
- **AND** a GitHub Release is published with generated notes

#### Scenario: Fix merge produces a patch release

- **GIVEN** the last release is `1.1.0`
- **AND** a commit `fix(config): correct visibility handling` is merged to `main`
- **WHEN** the release workflow runs
- **THEN** version `1.1.1` is computed

#### Scenario: Breaking change produces a major release

- **GIVEN** the last release is `1.1.1`
- **AND** a commit is merged whose type carries `!` or whose body contains a `BREAKING CHANGE:` footer
- **WHEN** the release workflow runs
- **THEN** version `2.0.0` is computed

#### Scenario: `!` marker is honored despite not being the plugin's built-in default

- **GIVEN** `commit-analyzer` and `release-notes-generator` are configured with
  `preset: "conventionalcommits"`
- **AND** a commit `feat(config)!: rename groups key to config_group` is merged
- **WHEN** the release workflow runs
- **THEN** version `2.0.0` is computed
- **AND** this would NOT happen under the plugins' built-in `angular` default, since that preset's
  header pattern does not capture `!`

#### Scenario: Non-releasing commit types produce no release

- **GIVEN** the only commits since the last release are of type `chore`, `docs`, `style`, `refactor`, `test`, `ci`, or `build`
- **WHEN** the release workflow runs
- **THEN** no version is computed
- **AND** no tag is created
- **AND** the workflow succeeds rather than failing

### Requirement: Prefixed Tag Format

The system SHALL create release tags prefixed with `v` (`v1.1.0`, `v1.1.1`), and `tagFormat` SHALL
be set explicitly to `v${version}`.

The two historical releases were tagged without the prefix (`1.0.0`, `1.0.1`). Those tags SHALL be
backfilled as `v1.0.0` and `v1.0.1` pointing at the same commits before the workflow is enabled,
because semantic-release resolves the last release only from tags matching `tagFormat`. A tag that
does not match is invisible to it. Absent the backfill, the workflow would find no prior release
and publish an initial `v1.0.0` rather than `v1.1.0`.

The unprefixed tags SHALL be retained. The Terraform Registry has published module versions
`1.0.0` and `1.0.1` resolved from them, and deleting a tag a published version depends on is
destructive to consumers pinning it.

#### Scenario: Tag is created with prefix

- **WHEN** version `1.1.0` is released
- **THEN** the git tag is named `v1.1.0`
- **AND** not `1.1.0`

#### Scenario: Prior release is resolved from the backfilled prefixed tag

- **GIVEN** the repository contains tags `1.0.0`, `1.0.1`, `v1.0.0`, and `v1.0.1`
- **WHEN** the release workflow determines the last release
- **THEN** `v1.0.1` is selected
- **AND** the unprefixed tags are ignored because they do not match `tagFormat`

#### Scenario: Missing backfill would misresolve the first release

- **GIVEN** `tagFormat` is `v${version}`
- **AND** no `v`-prefixed tag exists in the repository
- **WHEN** the release workflow runs
- **THEN** no prior release is found
- **AND** an initial `v1.0.0` would be published instead of `v1.1.0`

### Requirement: No Commits to the Default Branch

The release process SHALL NOT push commits to the default branch.

The `main` branch is governed by an active ruleset (`gjed-oss-main`) enforcing
`required_signatures`, `pull_request` review, `required_linear_history`, and `non_fast_forward`.
Commits created by an Actions token are unsigned and would be rejected. The release process SHALL
therefore not maintain an in-repository changelog file or version file, and release notes SHALL
live on the GitHub Release.

#### Scenario: No changelog commit is attempted

- **WHEN** a release is published
- **THEN** no commit is created on `main`
- **AND** no `CHANGELOG.md` is written to the repository
- **AND** the release notes are available on the GitHub Release

#### Scenario: Signed-commit ruleset does not block releasing

- **GIVEN** `main` enforces `required_signatures`
- **WHEN** the release workflow runs
- **THEN** the release succeeds
- **AND** the tag is created, because the ruleset targets branches and not tags

### Requirement: Release Workflow Trigger

The release workflow SHALL run on push to the default branch, and SHALL NOT be triggered by tag
creation. The tag is an output of the release, not its trigger.

The workflow SHALL check out full history with tags, since semantic-release cannot determine the
last release from a shallow clone.

#### Scenario: Push to main triggers a release evaluation

- **WHEN** a pull request is merged to `main`
- **THEN** the release workflow runs
- **AND** evaluates commits since the last release

#### Scenario: Tag push does not trigger a release

- **WHEN** a git tag is pushed to the repository
- **THEN** the release workflow does not run

#### Scenario: Full history is available to the workflow

- **WHEN** the release workflow checks out the repository
- **THEN** the full commit history and all tags are fetched
- **AND** the last release can be determined

### Requirement: Terraform Registry Publication

Releasing SHALL make the new version available on the Terraform Registry at
`registry.terraform.io/modules/gjed/config-as-yaml/github` without further action.

#### Scenario: Registry picks up the new version

- **GIVEN** the module is published to the Terraform Registry
- **WHEN** a release tag matching semantic versioning is created
- **THEN** the Registry publishes the corresponding module version
- **AND** consumers pinning a compatible constraint can resolve it
