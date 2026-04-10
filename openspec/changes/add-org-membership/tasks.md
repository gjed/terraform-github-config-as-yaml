# Tasks: Add Organization Membership Management

## 1. YAML Parsing for Membership

- [x] 1.1 Add membership directory loading in `yaml-config.tf` — add `membership_config_path`, `membership_files`, `membership_configs_by_file`, and `membership_config` locals following the existing pattern for `repository/`, `group/`, `ruleset/`, and `webhook/`. The directory MUST be optional (use `try()` like `webhook_files`).
- [x] 1.2 Add duplicate membership key detection — add `membership_key_occurrences` and `duplicate_membership_keys` locals following the existing `repo_key_occurrences`/`duplicate_repository_keys` pattern.
- [x] 1.3 Add `effective_membership` local that returns `{}` when `var.membership_management_enabled` is `false` OR `local.is_organization` is `false`, and returns `local.membership_config` otherwise.

## 2. Module Variables

- [x] 2.1 Add `membership_management_enabled` variable to `variables.tf` — boolean, default `false`, with description explaining the safety implications and SCIM/SSO conflict warning.

## 3. Membership Resource

- [x] 3.1 Add `github_membership` resource in `main.tf` — use `for_each` over `local.effective_membership`. Each entry maps `username` (key) and `role` (value). Place after the existing org-level resources.

## 4. Module Outputs

- [x] 4.1 Add `managed_members` output to `outputs.tf` — map of managed members with username and role, sourced from `github_membership` resources.
- [x] 4.2 Add `managed_member_count` output to `outputs.tf` — count of managed members.
- [x] 4.3 Update `duplicate_key_warnings` output to include membership duplicate warnings.

## 5. Template Configuration

- [x] 5.1 Create `config/membership/` directory with a commented-out example file (`example-members.yml`) showing the `username: role` format and documenting valid roles (`member`, `admin`).

## 6. Validation Script

- [x] 6.1 Update `scripts/validate-config.py` to validate membership configuration — check that the `membership/` directory (if present) contains valid YAML with string keys and values of `member` or `admin` only. Print a SCIM/SSO reminder when membership config is present.

## 7. Documentation

- [x] 7.1 Update `AGENTS.md` — add "Adding/managing organization members" section under Common Tasks, document `config/membership/` directory in Project Structure, and add SCIM/SSO conflict warning.
- [x] 7.2 Update `examples/consumer/` — add `membership_management_enabled = true` (commented out) to the consumer example with inline documentation.

## 8. Spec Updates

- [x] 8.1 Create spec delta at `openspec/changes/add-org-membership/specs/org-membership/spec.md` (done — verify with `openspec validate`).
- [x] 8.2 Create spec delta at `openspec/changes/add-org-membership/specs/module-interface/spec.md` (done — verify with `openspec validate`).
- [x] 8.3 Create spec delta at `openspec/changes/add-org-membership/specs/repository-management/spec.md` (done — verify with `openspec validate`).

## 9. Verification

- [x] 9.1 Run `terraform validate` with membership config present and `membership_management_enabled = true`.
- [x] 9.2 Run `terraform validate` with membership config present and `membership_management_enabled = false` (default) — confirm no membership resources in plan.
- [x] 9.3 Run `terraform validate` with membership directory missing — confirm no errors.
- [x] 9.4 Run `scripts/validate-config.py` — confirm membership validation works.
- [x] 9.5 Run `pre-commit run --all-files` — confirm no formatting or linting issues.
