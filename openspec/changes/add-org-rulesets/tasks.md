# Tasks: Add Organization-Level Rulesets

## Ordered Work Items

### 1. Parse and separate org rulesets in `yaml-config.tf`

Add a local that filters `rulesets_config` into two maps:
- `repo_rulesets_config` — entries without `scope` or with `scope: repository`
- `org_rulesets_config` — entries with `scope: organization`

This keeps the existing `merged_rulesets`/`effective_rulesets` logic working unchanged (it already
uses `rulesets_config` which will continue to contain only repo-scoped entries).

**Validates:** `terraform validate`; confirm org rulesets are separated from repo rulesets.

---

### 2. Apply subscription tier filtering for org rulesets

Add a local `org_rulesets_require_paid` that skips org rulesets when `subscription` is `free` or
`pro`, mirroring the existing `rulesets_require_paid_for_private` logic.

Add a local `effective_org_rulesets` that returns `{}` when the subscription is insufficient,
with a warning output similar to `repos_with_skipped_rulesets`.

**Validates:** Set `subscription: free` in `config.yml` and confirm org rulesets are not created.

---

### 3. Add `github_organization_ruleset` resource in `main.tf`

Create a new `resource "github_organization_ruleset" "this"` using `for_each` over
`local.effective_org_rulesets`. This resource mirrors the structure of
`github_repository_ruleset` in `modules/repository/main.tf` but uses
`repository_name` conditions from the org ruleset config.

The `conditions` block must support both `ref_name` and `repository_name` sub-blocks.
`repository_name` is optional (default: include `["*"]`, exclude `[]`).

**Validates:** `terraform plan` with an org ruleset defined; confirm resource appears in plan.

---

### 4. Update `config/ruleset/default-rulesets.yml` with an example org ruleset

Add a commented-out example org ruleset to the default ruleset config file to demonstrate
the `scope: organization` field and `repository_name` conditions.

**Validates:** Manual review; validate-config.py should not error.

---

### 5. Update `scripts/validate-config.py` to accept `scope` field

The validation script should recognise `scope: organization` and `scope: repository` as valid
fields on a ruleset definition. Org rulesets should also be checked to ensure they are not
referenced via `rulesets:` on repositories or groups (since org rulesets apply globally and
referencing them per-repo is a misconfiguration).

**Validates:** Run `scripts/validate-config.py` with org ruleset config; confirm no false errors.

---

### 6. Add spec delta for org ruleset management

Write the spec delta in `openspec/changes/add-org-rulesets/specs/org-ruleset-management/spec.md`
covering:
- `scope: organization` field on ruleset definitions
- `repository_name` conditions
- Subscription tier gating (team/enterprise only)
- org rulesets NOT being assignable to repos/groups via `rulesets:` key

**Validates:** `openspec validate add-org-rulesets --strict`

---

### 7. Update `repository-management` spec

Add a `MODIFIED` requirement to the existing `Repository Rulesets` requirement and a new
`Organization Rulesets` requirement. Update `Subscription Tier Awareness` to cover org rulesets.

**Validates:** `openspec validate add-org-rulesets --strict`

---

### 8. Update `AGENTS.md` and template YAML examples

Document the `scope` field in `AGENTS.md` ruleset docs and update the `config/ruleset/` example.

**Validates:** Manual review.

---

## Dependencies

- Tasks 1 → 2 → 3 (sequential: parsing feeds filtering feeds resource creation)
- Tasks 4, 5, 8 can run in parallel with each other after Task 1
- Tasks 6, 7 can run after all implementation tasks are drafted

## Parallelizable Work

- Tasks 4, 5, 8 are independent of each other
- Tasks 6, 7 are independent of each other and can be done once implementation shape is stable
