## 1. Configuration Loading

- [ ] 1.1 Add `branch_protection_config_path` local and `branch_protection_files` fileset in `yaml-config.tf`
- [ ] 1.2 Add `branch_protection_configs_by_file` local for per-file parsing
- [ ] 1.3 Add `branch_protections_config` merged map (all `.yml` files merged alphabetically)
- [ ] 1.4 Handle optional directory — use `try()` to fall back to empty map when directory is missing
- [ ] 1.5 Add duplicate key detection (`branch_protection_key_occurrences`, `duplicate_branch_protection_keys`)

## 2. Merging and Inheritance

- [ ] 2.1 Add `merged_branch_protections` local — collect from groups in order, append repo-specific, resolve by name
- [ ] 2.2 Add resolved branch protections to the `repositories` local map as `branch_protections`

## 3. Validation

- [ ] 3.1 Add `check` block to validate all branch protection references exist in `branch_protections_config`
- [ ] 3.2 Add duplicate branch protection keys to the `duplicate_config_keys` output

## 4. Module Variable

- [ ] 4.1 Add `branch_protections` variable to `modules/repository/variables.tf` with full type definition
- [ ] 4.2 Default to empty map `{}`

## 5. Module Resource

- [ ] 5.1 Add `github_branch_protection` resource in `modules/repository/main.tf` with `for_each`
- [ ] 5.2 Map top-level boolean fields (`enforce_admins`, `allows_deletions`, `allows_force_pushes`, `lock_branch`, `require_conversation_resolution`, `require_signed_commits`, `required_linear_history`)
- [ ] 5.3 Add dynamic `required_pull_request_reviews` block (only when sub-object is present)
- [ ] 5.4 Add dynamic `required_status_checks` block (only when sub-object is present)
- [ ] 5.5 Add dynamic `restrict_pushes` block (only when sub-object is present)

## 6. Root Module Pass-Through

- [ ] 6.1 Pass `branch_protections = each.value.branch_protections` in `main.tf` module call

## 7. Example Configuration

- [ ] 7.1 Create `config/branch-protection/default-protections.yml` with example definitions
- [ ] 7.2 Add `branch_protections` reference to an example group or repository config

## 8. Verification

- [ ] 8.1 Run `terraform fmt` on all changed `.tf` files
- [ ] 8.2 Run `terraform validate`
- [ ] 8.3 Run `terraform plan` with example config and verify branch protection resources appear
- [ ] 8.4 Run `pre-commit run --all-files`
