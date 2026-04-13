## ADDED Requirements

### Requirement: E2E fixture Terraform root module exists

A self-contained Terraform root module SHALL exist at `tests/e2e/` that references the
module root via `source = "../../"` and exposes `var.github_org`, `var.test_user`,
`var.webhook_secret`, and `var.membership_management_enabled`.

#### Scenario: Module can be initialised without credentials

- **WHEN** a developer runs `terraform init` in `tests/e2e/`
- **THEN** provider plugins download successfully and no errors are produced

#### Scenario: Module validates without a real org

- **WHEN** a developer runs `TF_VAR_github_org=placeholder terraform validate` in `tests/e2e/`
- **THEN** `terraform validate` exits 0 with "Success! The configuration is valid."

---

### Requirement: E2E fixture covers every module feature

The YAML config tree at `tests/e2e/config/` SHALL contain at least one example of every
feature supported by the module, as enumerated below. Each feature SHALL be exercised by
a named resource prefixed with `e2e-`.

Features that MUST be covered:

**Repositories:** public visibility, private visibility, `homepage_url`, all merge
strategies (`allow_merge_commit`, `allow_squash_merge`, `allow_rebase_merge`),
`allow_auto_merge`, `allow_update_branch`, `delete_branch_on_merge`,
`web_commit_signoff_required`, `vulnerability_alerts`, `license_template`, `topics`.

**Groups:** single-group inheritance, multi-group inheritance with scalar override by later
group, topics merge across groups, rulesets list from group, webhooks from group (string
reference), `branch_protections` from group, `actions` config in group.

**Rulesets (repository-scoped):** every rule type — `deletion`, `non_fast_forward`,
`required_linear_history`, `required_signatures`, `pull_request` (with all parameters),
`required_status_checks`, `commit_message_pattern`, `branch_name_pattern`; `bypass_actors`;
`target: tag`; `enforcement: evaluate`; template reference (`template:` key); inline
template override.

**Rulesets (org-scoped):** at least one ruleset with `scope: organization` and
`repository_name` conditions.

**Branch protections:** `pattern`, `enforce_admins`, `required_pull_request_reviews` (all
sub-fields), `required_status_checks`, `allows_deletions`, `allows_force_pushes`.

**Teams:** root team (tier 0), tier-1 child team, tier-2 grandchild team; `privacy: closed`,
`privacy: secret`; `review_request_delegation`.

**Webhooks:** repo-level string reference, repo-level inline definition, `content_type`,
`events`, `active`, `insecure_ssl`, `env:VAR_NAME` secret pattern; org-level webhook via
`org_webhooks` in `config.yml`.

**Actions (repo):** `allowed_actions: selected`, `github_owned_allowed`,
`verified_allowed`, `patterns_allowed` merged from multiple groups + repo.

**Actions (org):** `enabled_repositories`, `allowed_actions`, `allowed_actions_config`,
`default_workflow_permissions`, `can_approve_pull_request_reviews`.

**Org settings:** `billing_email`, `company`, `blog`, `default_repository_permission`,
`members_can_create_repositories`, `dependabot_alerts_enabled_for_new_repositories`,
`dependency_graph_enabled_for_new_repositories`.

**Partition loading:** a repository defined in a subdirectory partition
(`config/repository/partitioned/`) alongside top-level `*.yml` files.

#### Scenario: All declared repositories appear in Terraform outputs

- **WHEN** `terraform apply` completes successfully
- **THEN** `terraform output -json | jq '.repositories.value | keys'` lists every
  repository declared in `tests/e2e/config/repository/`

#### Scenario: Partition-loaded repo appears in outputs

- **WHEN** `terraform apply` completes with `repository_partitions = ["partitioned"]`
- **THEN** `e2e-partitioned-repo` appears in the `repositories` output

---

### Requirement: Subscription-gating outputs are exercised

The fixture, running with `subscription: free`, SHALL produce non-null
`subscription_warnings` and non-null `skipped_org_rulesets` outputs, demonstrating that
the subscription-tier gating logic fires correctly.

#### Scenario: subscription_warnings fires for private repo with ruleset on free tier

- **WHEN** `subscription: free` is set in `config/config.yml`
- **AND** a private repository references a ruleset
- **THEN** `terraform output subscription_warnings` is non-null and lists that repository

#### Scenario: skipped_org_rulesets fires for org-scoped ruleset on free tier

- **WHEN** `subscription: free` is set in `config/config.yml`
- **AND** at least one ruleset with `scope: organization` is defined
- **THEN** `terraform output skipped_org_rulesets` is non-null and lists that ruleset

---

### Requirement: Post-apply verification script asserts provisioned state

A Python script at `tests/verify_e2e.py` SHALL read `terraform output -json` from a file
argument, connect to the GitHub API using `GITHUB_TOKEN`, and assert that:

- Every repository in the `repositories` output exists on GitHub with the correct
  `visibility` value
- Every team in the `managed_teams` output exists on GitHub (by slug)
- `subscription_warnings` is non-null (on free tier with private rulesets)
- `skipped_org_rulesets` is non-null (on free tier with org ruleset)
- `org_webhooks` output contains `e2e-org-webhook`
- `duplicate_key_warnings` output is null
- `e2e-partitioned-repo` is present in the `repositories` output

The script SHALL exit 0 when all assertions pass and exit non-zero when any assertion fails,
printing a summary of passed and failed checks.

#### Scenario: All checks pass on a clean apply

- **WHEN** `terraform apply` completed without errors
- **AND** `GITHUB_TOKEN` is set with read access to the test org
- **WHEN** `python3 tests/verify_e2e.py /tmp/e2e_outputs.json` is run
- **THEN** the script exits 0 and prints "N passed, 0 failed"

#### Scenario: Script exits non-zero on missing repository

- **WHEN** a repository was not provisioned (e.g., apply skipped or destroyed)
- **THEN** the script exits non-zero and prints a failure line for that repository

---

### Requirement: E2E workflow is runnable via Makefile

A `Makefile` at `tests/e2e/` SHALL provide targets: `init`, `validate`, `plan`, `apply`,
`verify`, `destroy`, `clean`. The root `Makefile` SHALL delegate via `e2e-init`,
`e2e-plan`, `e2e-apply`, `e2e-verify`, `e2e-destroy` targets.

#### Scenario: Root Makefile delegates to tests/e2e/Makefile

- **WHEN** `make e2e-plan` is run from the repo root
- **THEN** `terraform plan` is executed inside `tests/e2e/`

---

### Requirement: Fixture is isolated and destroyable

All resources created by the fixture SHALL use the `e2e-` prefix. Running `terraform
destroy` in `tests/e2e/` SHALL remove all provisioned resources and leave no orphan
resources in the test org.

#### Scenario: Destroy removes all e2e resources

- **WHEN** `terraform destroy` is run after a successful apply
- **THEN** all `e2e-*` repositories, teams, rulesets, webhooks, and branch protections
  are removed from the test org

---

### Requirement: Setup is documented

A `README.md` at `tests/e2e/` SHALL document: prerequisites (test org, GitHub token,
webhook.site URLs), step-by-step run instructions, a feature coverage table, how to
enable team-tier testing (change `subscription` + upgrade org), and how to test membership
management.

#### Scenario: New contributor can follow README without prior knowledge

- **WHEN** a developer reads `tests/e2e/README.md`
- **THEN** they can set up and run the full E2E test without consulting any other document
