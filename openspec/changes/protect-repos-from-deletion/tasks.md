## 1. Repository Submodule Changes

- [x] 1.1 Hardcode `archive_on_destroy = true` on `github_repository.this` in `modules/repository/main.tf`, with an explanatory comment
- [x] 1.2 Confirm `prevent_destroy` is not set in the lifecycle block

## 2. Documentation

- [ ] 2.1 Add "Decommissioning a repository" section to AGENTS.md explaining the removal process and that repos are archived, not deleted
- [ ] 2.2 Document the hardcoded `archive_on_destroy = true` behavior as a module contract

## 3. Spec Updates

- [ ] 3.1 Archive the change specs into the main `openspec/specs/` directory after implementation is complete

## 4. Verification

- [ ] 4.1 Run `terraform fmt` and `terraform validate` to verify no syntax errors
- [ ] 4.2 Run `pre-commit run --all-files` to verify all hooks pass
