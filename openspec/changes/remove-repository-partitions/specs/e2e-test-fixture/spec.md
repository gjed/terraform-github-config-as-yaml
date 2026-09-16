## MODIFIED Requirements

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

**Subdirectory loading:** a repository defined in a subdirectory of `config/repository/`
(e.g. `config/repository/partitioned/`) alongside top-level `*.yml` files, loaded without
any selection variable.

#### Scenario: All declared repositories appear in Terraform outputs

- **WHEN** `terraform apply` completes successfully
- **THEN** `terraform output -json | jq '.repositories.value | keys'` lists every
  repository declared in `tests/e2e/config/repository/`

#### Scenario: Partition-loaded repo appears in outputs

- **WHEN** `terraform apply` completes
- **THEN** `e2e-partitioned-repo` (defined in `config/repository/partitioned/`) appears in the
  `repositories` output
