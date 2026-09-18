## 1. Repository Submodule Changes

- [x] 1.1 Add `archive_on_destroy` variable (default `true`) to `modules/repository/variables.tf`
- [x] 1.2 Set `archive_on_destroy = var.archive_on_destroy` on `github_repository.this` in `modules/repository/main.tf`
- [x] 1.3 Confirm `prevent_destroy` is not set in the lifecycle block

## 2. Root Module Wiring

- [x] 2.1 Add `archive_on_destroy` variable (default `true`) to `variables.tf`
- [x] 2.2 Pass `archive_on_destroy = var.archive_on_destroy` to the repository module in `main.tf`

## 3. E2E Fixture

- [x] 3.1 Set `archive_on_destroy = false` in `tests/e2e/main.tf` so throwaway repos are hard-deleted
- [x] 3.2 Update `openspec/specs/e2e-test-fixture/spec.md` and `tests/e2e/README.md` destroy contract

## 4. Documentation

- [x] 4.1 Add "Decommissioning a repository" section to AGENTS.md explaining the removal process and
      that repos are archived, not deleted
- [x] 4.2 Document the `archive_on_destroy` behavior (default `true`)

## 5. Spec Updates

- [ ] 5.1 Archive the change specs into the main `openspec/specs/` directory after implementation is complete

## 6. Verification

- [x] 6.1 Run `terraform fmt` and `terraform validate` to verify no syntax errors
- [ ] 6.2 Run `pre-commit run --all-files` to verify all hooks pass
