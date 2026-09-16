## 1. Repository Submodule Changes

- [ ] 1.1 Add `archive_on_destroy` variable to `modules/repository/variables.tf` (type bool, default false, with description)
- [ ] 1.2 Add `archive_on_destroy = var.archive_on_destroy` to the `github_repository.this` resource in `modules/repository/main.tf`

## 2. YAML Configuration Layer

- [ ] 2.1 Add `archive_on_destroy: false` to the `defaults:` block in `config/config.yml` (with comment explaining the setting and future default flip)
- [ ] 2.2 Read `archive_on_destroy` from `local.common_config.defaults` in `yaml-config.tf`, defaulting to `false` when absent
- [ ] 2.3 Include `archive_on_destroy` in the `local.repositories` map in `yaml-config.tf`

## 3. Root Module Wiring

- [ ] 3.1 Pass `archive_on_destroy` from `local.repositories` to the repository module call in `main.tf`

## 4. Validation Script

- [ ] 4.1 Add a warning in `scripts/validate-config.py` when `defaults.archive_on_destroy` is explicitly set to `false`

## 5. Documentation

- [ ] 5.1 Add "Decommissioning a repository" section to AGENTS.md explaining the removal process
- [ ] 5.2 Document the `archive_on_destroy` setting in the defaults section of AGENTS.md, noting default is `false` in this release
- [ ] 5.3 Note the deferred `archive_on_destroy` default-to-`true` flip for the next major version

## 6. Spec Updates

- [ ] 6.1 Archive the change specs into the main `openspec/specs/` directory after implementation is complete

## 7. Verification

- [ ] 7.1 Run `terraform fmt` and `terraform validate` to verify no syntax errors
- [ ] 7.2 Run `pre-commit run --all-files` to verify all hooks pass
- [ ] 7.3 Run the validation script to confirm no unexpected warnings
