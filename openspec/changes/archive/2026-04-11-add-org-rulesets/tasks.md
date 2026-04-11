# Tasks: Add Organization-Level Rulesets

## Ordered Work Items

- [x] Task 1: Parse and separate org rulesets in `yaml-config.tf`
  — add `repo_rulesets_config` and `org_rulesets_config` locals split by `scope`
- [x] Task 2: Apply subscription tier filtering for org rulesets
  — add `org_rulesets_require_paid`, `effective_org_rulesets`; add `skipped_org_rulesets` output
- [x] Task 3: Add `github_organization_ruleset` resource in `main.tf`
  — `for_each` over `local.effective_org_rulesets` with `ref_name` + optional `repository_name`
- [x] Task 4: Update `config/ruleset/default-rulesets.yml` with a commented-out example
  org ruleset demonstrating `scope: organization` and `repository_name` conditions
- [x] Task 5: Update `scripts/validate-config.py` to accept `scope` field on rulesets
  and warn when org rulesets are referenced per-repository or per-group
- [x] Task 6: Add spec delta for org ruleset management
  (already written at `specs/org-ruleset-management/spec.md`)
- [x] Task 7: Update `repository-management` spec — add `MODIFIED` requirement for
  Repository Rulesets and new `Organization Rulesets` requirement
- [x] Task 8: Update `AGENTS.md` and template YAML examples to document the `scope` field

## Dependencies

- Tasks 1 → 2 → 3 (sequential: parsing feeds filtering feeds resource creation)
- Tasks 4, 5, 8 can run in parallel with each other after Task 1
- Tasks 6, 7 can run after all implementation tasks are drafted
