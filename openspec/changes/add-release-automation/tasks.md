## 1. Configuration

- [ ] 1.1 Create `.releaserc.json` with `tagFormat: "v${version}"`
- [ ] 1.2 Configure `commit-analyzer` and `release-notes-generator` with `preset: "conventionalcommits"`
      (not the plugins' `angular` default, which does not recognize `feat!:`)
- [ ] 1.3 Plugin list: `commit-analyzer`, `release-notes-generator`, `github` only — no `git`,
      no `changelog`, no `npm` (see design.md for why)

## 2. Workflow

- [ ] 2.1 Create `.github/workflows/release.yml` triggered on `push: branches: [main]`
- [ ] 2.2 `permissions: contents: write, issues: write, pull-requests: write`
- [ ] 2.3 Checkout with `fetch-depth: 0` (full history + tags required for version detection)
- [ ] 2.4 Run `cycjimmy/semantic-release-action@v6` with `GITHUB_TOKEN`

## 3. Tag backfill (prerequisite — must land before the workflow runs)

- [ ] 3.1 Create `v1.0.0` on `e6b4cc9` and `v1.0.1` on `4b1e2a1`, matching the existing
      unprefixed `1.0.0` / `1.0.1` tags
- [ ] 3.2 Push both to `origin` — `origin` currently has no `v`-prefixed tag at all
- [ ] 3.3 Retain the unprefixed `1.0.0` / `1.0.1` tags; the Registry's published versions resolve
      from them and deleting them would break consumers pinning those versions

## 4. Verification

- [ ] 4.1 Verify `tagFormat: "v${version}"` resolves the last release as `v1.0.1` once the
      backfill is pushed
- [ ] 4.2 Dry run: `npx semantic-release --dry-run` against the pushed branch, confirm it reports
      `v1.1.0` as the next version (no `!` or `BREAKING CHANGE:` commit since `1.0.1`)
- [ ] 4.3 Confirm the workflow does not attempt any commit or push to `main`
- [ ] 4.4 Confirm neither active ruleset (`gjed-oss-main`, `oss-main-protection`) blocks tag
      creation — both target `branch`, not `tag`

## 5. Decommission manual release

- [ ] 5.1 Document in `CONTRIBUTING.md` that releases happen automatically on merge to `main` and
      that commit type determines the version bump. (No manual-release instructions exist in
      `README.md`, `CONTRIBUTING.md`, or `Makefile` to remove — verified.)
- [ ] 5.2 First-run version decided: accept `v1.1.0`, with the `vulnerability_alerts` state change
      noted in the release notes

## 6. First release

- [ ] 6.1 Merge this change to `main`. **This merge publishes `v1.1.0` immediately.** The workflow
      analyzes every commit since the last release (`v1.0.1`), and those 74 commits already
      include `feat:` entries — so a release fires on the first run regardless of this PR's own
      commit type. It is not deferred to some later `feat`/`fix` merge.
- [ ] 6.2 Confirm the resulting `v1.1.0` tag appears on `origin`
- [ ] 6.3 Confirm the Terraform Registry lists the new version at
      `registry.terraform.io/modules/gjed/config-as-yaml/github`
