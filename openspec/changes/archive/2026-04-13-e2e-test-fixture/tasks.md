## 1. Terraform root module

- [x] 1.1 Create `tests/e2e/main.tf` — provider block (`owner = var.github_org`), module call to `../../` with `config_path`, `repository_partitions = ["partitioned"]`, `webhook_secrets`, `membership_management_enabled`
- [x] 1.2 Create `tests/e2e/variables.tf` — `github_org` (string), `test_user` (string, default `""`), `webhook_secret` (string, sensitive, default `"e2e-test-secret"`), `membership_management_enabled` (bool, default `false`)
- [x] 1.3 Create `tests/e2e/outputs.tf` — mirror all module outputs: `repositories`, `repository_count`, `organization`, `subscription_tier`, `subscription_warnings`, `skipped_org_rulesets`, `duplicate_key_warnings`, `managed_members`, `managed_member_count`, `managed_teams`, `team_count`, `org_webhooks` (sensitive), `security_manager_teams`, `organization_settings_warnings`
- [x] 1.4 Create `tests/e2e/.gitignore` — ignore `.terraform/`, `.terraform.lock.hcl`, `tfplan`, `*.tfstate`, `*.tfstate.backup`, `terraform.tfvars`
- [x] 1.5 Verify: `cd tests/e2e && terraform init && TF_VAR_github_org=placeholder terraform validate` exits 0

## 2. Org-level config

- [x] 2.1 Create `tests/e2e/config/config.yml` — `organization: REPLACE_WITH_YOUR_TEST_ORG`, `subscription: free`, `is_organization: true`, full `settings:` block (billing_email, company, blog, email, location, description, default_repository_permission, members_can_create_repositories, members_can_create_public_repositories, members_can_create_private_repositories, members_can_fork_private_repositories, web_commit_signoff_required, dependabot_alerts_enabled_for_new_repositories, dependabot_security_updates_enabled_for_new_repositories, dependency_graph_enabled_for_new_repositories), `actions:` block (enabled_repositories: all, allowed_actions: selected, allowed_actions_config with github_owned_allowed/verified_allowed/patterns_allowed, default_workflow_permissions: read, can_approve_pull_request_reviews: false), `org_webhooks: [e2e-org-webhook]`, commented-out `security:` block

## 3. Groups

- [x] 3.1 Create `tests/e2e/config/group/test-groups.yml` with four groups:
  - `base`: empty teams map
  - `oss-e2e`: public visibility, has_issues/wiki/discussions, all merge strategies, delete_branch_on_merge, web_commit_signoff_required, topics `[e2e, oss-e2e]`, `rulesets: [e2e-oss-protection]`, `webhooks: [e2e-webhook]`
  - `internal-e2e`: private visibility, has_issues, topics `[e2e, internal-e2e]`, `rulesets: [e2e-internal-protection]`, `branch_protections: [e2e-main-bp]`
  - `restricted-actions-e2e`: `actions:` block with `allowed_actions: selected`, `github_owned_allowed: true`, `verified_allowed: false`, `patterns_allowed: ["actions/checkout@*", "actions/setup-node@*"]`

## 4. Webhooks

- [x] 4.1 Create `tests/e2e/config/webhook/test-webhooks.yml` with two entries:
  - `e2e-webhook`: url `https://webhook.site/00000000-0000-0000-0000-000000000001`, content_type: json, `secret: env:E2E_WEBHOOK_SECRET`, events `[push, pull_request, create, delete]`, active: true, insecure_ssl: false
  - `e2e-org-webhook`: url `https://webhook.site/00000000-0000-0000-0000-000000000002`, content_type: json, no secret, events `[repository, member, organization]`, active: true

## 5. Rulesets

- [x] 5.1 Create `tests/e2e/config/ruleset/test-rulesets.yml` with:
  - `e2e-oss-protection`: branch, active, `~DEFAULT_BRANCH`, rules: deletion + non_fast_forward + required_linear_history + pull_request (all 5 parameters)
  - `e2e-internal-protection`: branch, active, `~DEFAULT_BRANCH`, rules: deletion + non_fast_forward + required_signatures
  - `e2e-require-ci`: branch, active, `~DEFAULT_BRANCH`, rules: required_status_checks (contexts: ci/build + ci/test, strict: true)
  - `e2e-commit-convention`: branch, **evaluate** enforcement, `~DEFAULT_BRANCH`, rules: commit_message_pattern (regex, conventional commits pattern)
  - `e2e-tag-protection`: **tag** target, active, `refs/tags/v*`, bypass_actors (RepositoryRole actor_id 5 always), rules: deletion + update
  - `e2e-branch-naming`: branch, active, `refs/heads/*` exclude main/devel, rules: branch_name_pattern (regex)
  - `e2e-strict-template`: template ruleset (branch, active, `~DEFAULT_BRANCH`, deletion + non_fast_forward + required_linear_history + pull_request with required_approving_review_count: 2, require_code_owner_review: true)
  - `e2e-org-protection`: `scope: organization`, branch, active, `~DEFAULT_BRANCH`, repository_name include `e2e-*` exclude `e2e-sandbox-*`, rules: deletion + non_fast_forward

## 6. Branch protections

- [x] 6.1 Create `tests/e2e/config/branch-protection/test-branch-protections.yml` with two entries:
  - `e2e-main-bp`: pattern: main, enforce_admins: false, allows_deletions: false, allows_force_pushes: false, require_conversation_resolution: true, require_signed_commits: false, required_linear_history: false, required_pull_request_reviews (count 1, dismiss_stale: true, code_owner: false, last_push: false, restrict_dismissals: false), required_status_checks (strict: false, contexts: [])
  - `e2e-strict-bp`: pattern: main, enforce_admins: true, allows_deletions: false, allows_force_pushes: false, lock_branch: false, require_conversation_resolution: true, require_signed_commits: true, required_linear_history: true, required_pull_request_reviews (count 2, all booleans true except restrict_dismissals), required_status_checks (strict: true, contexts: [ci/build, ci/test])

## 7. Teams

- [x] 7.1 Create `tests/e2e/config/team/test-teams.yml` with a 3-level hierarchy:
  - Root `e2e-platform`: description, privacy: closed, members: [], maintainers: [], review_request_delegation: null
  - Child `e2e-backend` (under e2e-platform): description, privacy: closed, members: [], maintainers: [], review_request_delegation with algorithm: ROUND_ROBIN, member_count: 0, notify: false
  - Grandchild `e2e-api` (under e2e-backend): description, privacy: **secret**, members: [], maintainers: [], review_request_delegation: null

## 8. Membership

- [x] 8.1 Create `tests/e2e/config/membership/test-members.yml` — comment-only file with the placeholder `# YOUR_GITHUB_USERNAME: member` and a warning comment that membership is disabled by default

## 9. Repositories

- [x] 9.1 Create `tests/e2e/config/repository/test-repos.yml` with these repos:
  - `e2e-oss-public`: groups `[base, oss-e2e]`, homepage_url, license_template: mit, topics: [terraform]
  - `e2e-internal-private`: groups `[base, internal-e2e]`
  - `e2e-multi-group`: groups `[base, internal-e2e, restricted-actions-e2e]`
  - `e2e-full-featured`: groups `[base, oss-e2e]`, repo-level scalar overrides (has_discussions: false, allow_merge_commit: false, web_commit_signoff_required: false), topics: [full-featured], rulesets: [e2e-require-ci, e2e-commit-convention, `{template: e2e-strict-template}`, `{template: e2e-strict-template, rules: [{type: pull_request, parameters: {required_approving_review_count: 1, dismiss_stale_reviews_on_push: false}}]}`], branch_protections: [e2e-strict-bp], inline webhook `e2e-inline-webhook` with url/events/active
  - `e2e-actions-restricted`: groups `[base, oss-e2e, restricted-actions-e2e]`, repo-level actions block adding `e2e-test-org/custom-action@*` to patterns_allowed
  - `e2e-private-override`: groups `[base, oss-e2e]`, `visibility: private` (overrides group public)
  - `e2e-with-tag-ruleset`: groups `[base, oss-e2e]`, rulesets: [e2e-tag-protection, e2e-branch-naming]
- [x] 9.2 Create `tests/e2e/config/repository/partitioned/partitioned-repos.yml` — single repo `e2e-partitioned-repo`: groups `[base, oss-e2e]`, topics: [partitioned]

## 10. Makefile and tfvars

- [x] 10.1 Create `tests/e2e/Makefile` with targets: `help`, `init`, `validate`, `plan`, `plan-show`, `apply`, `verify`, `destroy`, `clean`; `verify` target does `terraform output -json > /tmp/e2e_outputs.json && python3 ../verify_e2e.py /tmp/e2e_outputs.json`
- [x] 10.2 Create `tests/e2e/terraform.tfvars.example` with `github_org`, `test_user`, `webhook_secret`, `membership_management_enabled` with comments explaining each
- [x] 10.3 Append `e2e-init`, `e2e-validate`, `e2e-plan`, `e2e-apply`, `e2e-verify`, `e2e-destroy` delegating targets to root `Makefile` using `$(MAKE) -C tests/e2e <target>`

## 11. Verification script

- [x] 11.1 Create `tests/verify_e2e.py` with: CLI argument for outputs JSON file path, `GITHUB_TOKEN` env var check, `CheckResult` dataclass tracking passed/failed with `ok()`, `fail()`, `assert_eq()`, `assert_contains()` helpers
- [x] 11.2 Implement `verify_repositories()` — for each repo in outputs, call `gh_org.get_repo(name)` and assert `visibility` matches
- [x] 11.3 Implement `verify_teams()` — for each team slug in outputs, call `gh_org.get_team_by_slug(slug)` and assert it exists
- [x] 11.4 Implement `verify_subscription_warnings()` — assert non-null on free tier and `e2e-internal-private` is in `repos` list
- [x] 11.5 Implement `verify_skipped_org_rulesets()` — assert non-null on free/pro tier, null on team/enterprise
- [x] 11.6 Implement `verify_org_webhooks()` — assert `e2e-org-webhook` key present in output
- [x] 11.7 Implement `verify_no_duplicate_warnings()` — assert `duplicate_key_warnings` output is null
- [x] 11.8 Implement `verify_partitioned_repo_loaded()` — assert `e2e-partitioned-repo` in repositories output
- [x] 11.9 Wire all checks into `main()` with section headers; print summary "N passed, N failed"; exit 0 on all pass, non-zero on any failure
- [x] 11.10 `chmod +x tests/verify_e2e.py` and verify: `python3 -m py_compile tests/verify_e2e.py`

## 12. README

- [x] 12.1 Create `tests/e2e/README.md` with sections: Prerequisites (test org, token scopes, webhook.site, PyGithub), Running the E2E Test (init/plan/apply/verify/destroy commands), Feature Coverage table (one row per feature → config location → repo name), Testing Team/Enterprise Features (how to change subscription + upgrade org), Testing Membership Management (edit membership YAML + tfvars override), Cleanup warning

## 13. Commit

- [x] 13.1 Validate all YAML files parse cleanly: `for f in $(find tests/e2e/config -name '*.yml'); do python3 -c "import yaml; yaml.safe_load(open('$f'))" || echo "FAILED: $f"; done`
- [x] 13.2 Run `terraform validate` in `tests/e2e/`: `cd tests/e2e && terraform init -backend=false && TF_VAR_github_org=placeholder terraform validate`
- [x] 13.3 Run `python3 -m py_compile tests/verify_e2e.py`
- [x] 13.4 Commit all new and modified files: `git add tests/ Makefile && git commit -m "feat(test): add e2e test fixture covering all module features"`
