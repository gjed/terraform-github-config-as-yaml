## 1. MCP declaration

- [x] 1.1 Add `.mcp.json` with `terraform` (registry lookup, no auth) and `github`
  (read-only, `${GITHUB_TOKEN}` env expansion) stdio servers

## 2. Consumer skills (`skills/`)

- [x] 2.1 `manage-repo-config` — add/modify/remove repos, group merge semantics, tier gating,
  validate + plan workflow
- [x] 2.2 `plan-safety-review` — parse `terraform show -json tfplan`, flag destroys,
  visibility flips, member removals
- [x] 2.3 `ruleset-authoring` — repository vs organization rulesets, rule types, tier gating
- [x] 2.4 `onboard-offboard` — `onboard-repos.sh` / `offboard-repos.sh` / `migrate-state.sh`
  usage and safety rails

## 3. Maintainer skills (`skills/internal/`)

- [x] 3.1 `e2e-testing` — `make e2e-*` lifecycle, fixture prerequisites, teardown
- [x] 3.2 `openspec-workflow` — proposal/spec/tasks flow, spec commit types, archive

## 4. Verification

- [x] 4.1 `pre-commit run --all-files` (markdownlint on all new skill files)
- [x] 4.2 `openspec validate add-agent-skills --strict`
