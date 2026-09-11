## 1. Configuration

- [x] 1.1 Create `.releaserc.json` with `tagFormat: "v${version}"`
- [x] 1.2 Configure `commit-analyzer` and `release-notes-generator` with `preset: "conventionalcommits"`
      (not the plugins' `angular` default, which does not recognize `feat!:`)
- [x] 1.3 Plugin list: `commit-analyzer`, `release-notes-generator`, `github` only — no `git`,
      no `changelog`, no `npm` (see design.md for why)
- [x] 1.4 Install `conventional-changelog-conventionalcommits` via the action's `extra_plugins`.
      Neither analyzer plugin bundles it; without it the run aborts with `MODULE_NOT_FOUND`
      before creating a tag.
- [x] 1.5 Pin the preset to `9.x`. Preset `10.x` needs `conventional-changelog-writer >= 9` while
      semantic-release 25 resolves writer `^8`, failing note generation with `Missing helper`.

## 2. Workflow

- [x] 2.1 Create `.github/workflows/release.yml` triggered on `push: branches: [main]`
- [x] 2.2 `permissions: contents: write, issues: write, pull-requests: write`
- [x] 2.3 Checkout with `fetch-depth: 0` (full history + tags required for version detection)
- [x] 2.4 Run `cycjimmy/semantic-release-action@v6` with `GITHUB_TOKEN`
- [x] 2.5 Add a `concurrency` group with `cancel-in-progress: false` so overlapping runs queue
      instead of racing to publish the same version

## 3. Tag backfill (prerequisite — completed)

- [x] 3.1 Create `v1.0.0` on `e6b4cc9` and `v1.0.1` on `4b1e2a1`, matching the existing
      unprefixed `1.0.0` / `1.0.1` tags
- [x] 3.2 Push both to `origin`
- [x] 3.3 Retain the unprefixed `1.0.0` / `1.0.1` tags; the Registry's published versions resolve
      from them and deleting them would break consumers pinning those versions

`origin` now carries all four tags — `1.0.0`, `1.0.1`, `v1.0.0`, `v1.0.1` — with each prefixed tag
pointing at the same commit as its unprefixed counterpart.

## 4. Verification

- [x] 4.1 `tagFormat: "v${version}"` resolves the last release as `v1.0.1` — confirmed by dry-run
      analyzing exactly the commits after that tag
- [x] 4.2 Dry run against the real remote branch: **77 commits analyzed, minor release, next
      version `1.1.0`**. Run with node 24 and the preset installed; both plugins loaded clean and
      notes rendered without error.
- [x] 4.3 Confirm the workflow does not attempt any commit or push to `main` — no `git` or
      `changelog` plugin is configured
- [x] 4.4 Confirm neither active ruleset (`gjed-oss-main`, `oss-main-protection`) blocks tag
      creation — both target `branch`, not `tag`

## 5. Decommission manual release

- [x] 5.1 Document in `CONTRIBUTING.md` that releases happen automatically on merge to `main` and
      that commit type determines the version bump. (No manual-release instructions exist in
      `README.md`, `CONTRIBUTING.md`, or `Makefile` to remove — verified.)
- [x] 5.2 First-run version decided: accept `v1.1.0`

## 6. First release

- [ ] 6.1 Merge this change to `main`. **This merge publishes `v1.1.0` immediately.** The workflow
      analyzes every commit since the last release (`v1.0.1`), and those already include `feat:`
      entries — so a release fires on the first run regardless of this PR's own commit type. It is
      not deferred to some later `feat`/`fix` merge.
- [ ] 6.2 Confirm the resulting `v1.1.0` tag appears on `origin`
- [ ] 6.3 **Manual, one-time:** edit the `v1.1.0` GitHub Release body to prepend an upgrade note
      for the `vulnerability_alerts` migration (`9aec9a4`). Generated notes come from commit text,
      and that commit's subject does not state the consumer-visible state change — the dry-run
      confirms it renders as a plain `fix(repository):` bullet with no warning. Not automated:
      permanent machinery for one historical commit is not worth carrying.
- [ ] 6.4 Confirm the Terraform Registry lists the new version at
      `registry.terraform.io/modules/gjed/config-as-yaml/github`
