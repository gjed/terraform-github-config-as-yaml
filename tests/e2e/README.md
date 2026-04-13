# E2E Test Fixture

A self-contained Terraform root module that provisions a complete GitHub organization
using every feature of `terraform-github-config-as-yaml`, then verifies the result
via the GitHub API.

---

## Prerequisites

### 1. Dedicated test organization

Create a **throwaway** GitHub organization (e.g., `my-username-e2e-test`). Do **not** use
a real org — this fixture creates, modifies, and deletes repositories and teams.

Free-tier orgs work out of the box. To test Team-tier features (org rulesets, security
managers), upgrade the org to Team (or use an existing Team org).

### 2. GitHub token

Create a **classic** personal access token with these scopes:

- `admin:org` — manage org settings, webhooks, teams, members
- `repo` — create and manage repositories (includes private repos)
- `delete_repo` — destroy repositories on `terraform destroy`

Set the token in your environment:

```bash
export GITHUB_TOKEN=ghp_your_token_here
```

### 3. webhook.site URLs (optional)

The fixture references two webhook.site URLs as placeholders. Webhook delivery failures
do **not** block `terraform apply`. If you want live delivery, replace the URLs in
`config/webhook/test-webhooks.yml` with fresh URLs from <https://webhook.site>.

### 4. PyGithub (for verify step only)

```bash
pip install PyGithub
```

---

## Running the E2E Test

### Step 1 — Configure

```bash
cd tests/e2e
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: set github_org to your test org name
```

### Step 2 — Initialize

```bash
make init
# or from the repo root:
make e2e-init
```

### Step 3 — Validate (no credentials needed)

```bash
make validate
```

### Step 4 — Plan

```bash
make plan
```

Review the plan output carefully. All resources will be prefixed with `e2e-`.

### Step 5 — Apply

```bash
make apply
```

This creates real GitHub resources in your test org. Expect ~30–60 seconds.

### Step 6 — Verify

```bash
make verify
```

Runs `tests/verify_e2e.py` against the live GitHub API. Exits 0 on success.

### Step 7 — Destroy

```bash
make destroy
```

**Always run this after testing.** Removes all `e2e-*` resources from the org.

---

## Feature Coverage

| Feature | Config location | Test resource |
|---|---|---|
| Public repository | `config/repository/test-repos.yml` | `e2e-oss-public` |
| Private repository | `config/repository/test-repos.yml` | `e2e-internal-private` |
| Visibility override (public→private) | `config/repository/test-repos.yml` | `e2e-private-override` |
| Multi-group inheritance | `config/repository/test-repos.yml` | `e2e-multi-group` |
| Per-repo scalar overrides | `config/repository/test-repos.yml` | `e2e-full-featured` |
| `homepage_url`, `license_template` | `config/repository/test-repos.yml` | `e2e-oss-public` |
| Topics merge across groups | `config/group/test-groups.yml` | all repos |
| Repository partition loading | `config/repository/partitioned/` | `e2e-partitioned-repo` |
| Group: base | `config/group/test-groups.yml` | `base` |
| Group: oss-e2e (public, rulesets, webhook) | `config/group/test-groups.yml` | `oss-e2e` |
| Group: internal-e2e (private, branch prot.) | `config/group/test-groups.yml` | `internal-e2e` |
| Group: restricted-actions-e2e | `config/group/test-groups.yml` | `restricted-actions-e2e` |
| Repo ruleset (branch, deletion+PR) | `config/ruleset/test-rulesets.yml` | `e2e-oss-protection` |
| Repo ruleset (required_signatures) | `config/ruleset/test-rulesets.yml` | `e2e-internal-protection` |
| Repo ruleset (required_status_checks) | `config/ruleset/test-rulesets.yml` | `e2e-require-ci` |
| Repo ruleset (commit_message_pattern, evaluate) | `config/ruleset/test-rulesets.yml` | `e2e-commit-convention` |
| Repo ruleset (tag target, bypass_actors) | `config/ruleset/test-rulesets.yml` | `e2e-tag-protection` |
| Repo ruleset (branch_name_pattern) | `config/ruleset/test-rulesets.yml` | `e2e-branch-naming` |
| Ruleset template + inline override | `config/repository/test-repos.yml` | `e2e-full-featured` |
| Org ruleset (`scope: organization`) | `config/ruleset/test-rulesets.yml` | `e2e-org-protection` |
| `subscription_warnings` output (free tier) | `config/config.yml` | `e2e-internal-private` |
| `skipped_org_rulesets` output (free tier) | `config/ruleset/test-rulesets.yml` | `e2e-org-protection` |
| Branch protection (basic) | `config/branch-protection/test-branch-protections.yml` | `e2e-main-bp` |
| Branch protection (strict, all fields) | `config/branch-protection/test-branch-protections.yml` | `e2e-strict-bp` |
| Team tier 0 (root) | `config/team/test-teams.yml` | `e2e-platform` |
| Team tier 1 (child, round-robin delegation) | `config/team/test-teams.yml` | `e2e-backend` |
| Team tier 2 (grandchild, secret) | `config/team/test-teams.yml` | `e2e-api` |
| Repo webhook (string ref, env secret) | `config/webhook/test-webhooks.yml` | `e2e-webhook` |
| Repo webhook (inline definition) | `config/repository/test-repos.yml` | `e2e-full-featured` |
| Org webhook | `config/webhook/test-webhooks.yml` | `e2e-org-webhook` |
| Repo Actions config (restricted) | `config/group/test-groups.yml` | `e2e-actions-restricted` |
| Org Actions config | `config/config.yml` | org-level |
| Org settings (billing_email, company, etc.) | `config/config.yml` | org-level |
| Membership management (disabled by default) | `config/membership/test-members.yml` | — |

---

## Testing Team/Enterprise Features

### Org rulesets (requires Team or Enterprise org)

1. Upgrade your test org to the Team plan
2. Edit `tests/e2e/config/config.yml`: change `subscription: free` to `subscription: team`
3. Re-run `make plan && make apply`

The `e2e-org-protection` ruleset (currently skipped on free tier) will now be applied.
`skipped_org_rulesets` output will be null.

### Security manager teams (requires Team or Enterprise org)

1. Upgrade your test org and set `subscription: team`
2. Uncomment the `security:` block in `tests/e2e/config/config.yml`
3. Re-run `make plan && make apply`

---

## Testing Membership Management

> ⚠️ **High risk.** Read carefully before enabling.

1. Edit `tests/e2e/config/membership/test-members.yml`:

   ```yaml
   your_github_username: member
   ```

2. Edit `terraform.tfvars`:

   ```hcl
   membership_management_enabled = true
   ```

3. Run `terraform plan` and review the output — confirm only the expected ADD appears.

4. Run `terraform apply`.

5. When done, remove the username from `test-members.yml` and `terraform apply` again
   to clean up before running `terraform destroy`.

---

## Cleanup

After every test run:

```bash
make destroy
```

If destroy fails partway through, you can re-run it or manually delete `e2e-*` repos
and teams from the GitHub org UI. The `e2e-` prefix makes them easy to find.
