## 1. Point the fixture at the test organization

- [x] 1.1 Set `github_org = "gjed-io"` in `tests/e2e/terraform.tfvars.example`
- [x] 1.2 Set `organization: gjed-io` in `tests/e2e/config/config.yml`
- [x] 1.3 Document in both files that forks must change them

## 2. Close verification gaps

- [x] 2.1 Add `skipped_branch_protections` to `tests/e2e/outputs.tf`
- [x] 2.2 `verify_skipped_branch_protections` — free tier lists private repos, excludes public
- [x] 2.3 `verify_branch_protection_state` — confirm live state via the GitHub API
- [x] 2.4 `verify_vulnerability_alerts` — assert alerts enabled on every repository
- [x] 2.5 Handle the empty-repository case (no default branch) without failing
- [x] 2.6 Register all three checks in `main()`

## 3. Fine-grained token

- [x] 3.1 Rewrite the README token section for fine-grained PATs with the exact permissions
- [x] 3.2 Update the `make help` prerequisite text
- [x] 3.3 Update the error message in `verify_e2e.py` when `GITHUB_TOKEN` is unset

## 4. Dependencies

- [x] 4.1 Add `tests/e2e/requirements.txt` declaring PyGithub
- [x] 4.2 Point the README at `pip install -r requirements.txt`

## 5. Workflow

- [x] 5.1 Add `.github/workflows/e2e.yml` on `workflow_dispatch` + nightly `schedule`
- [x] 5.2 No `pull_request` trigger
- [x] 5.3 Gate credentials behind the `e2e` environment
- [x] 5.4 Fail fast with an explicit error when the token or org var is missing
- [x] 5.5 Destroy with `if: always()`, plus a `skip_destroy` dispatch input that warns
- [x] 5.6 Concurrency group that queues rather than cancels
- [x] 5.7 Pin actions to current majors, minimal `permissions`, job timeout

## 6. Documentation

- [x] 6.1 Add `skipped_branch_protections` and vulnerability alerts to the coverage table
- [x] 6.2 Explain which features a free-tier org skips, and that verification asserts the skips

## 7. Verify

- [x] 7.1 `terraform validate` passes in `tests/e2e`
- [x] 7.2 `tests/verify_e2e.py` compiles; PyGithub API methods confirmed present
- [x] 7.3 yamllint and check-yaml pass on the new workflow
- [x] 7.4 markdownlint passes on the README
- [x] 7.5 `openspec validate add-e2e-ci-workflow --strict` passes

## 8. Manual setup required before the workflow can succeed

These cannot be done from the repository and are the owner's to perform:

- [x] 8.1 Create a fine-grained PAT scoped to `gjed-io` with the permissions in the README
- [x] 8.2 Create the `e2e` environment in repository settings
- [x] 8.3 Add `E2E_GITHUB_TOKEN` (secret) and `E2E_GITHUB_ORG` (variable) to that environment
- [x] 8.4 Dispatch the workflow manually once and confirm a green run before relying on the
  schedule — verified via direct `terraform apply`/`verify_e2e.py`/`terraform destroy` against
  `gjed-io` in fix-actions-tier-conflict (45 resources, 33/33 checks, clean teardown); the
  nightly schedule (04:00 UTC) has run with every fix in place as of this change

## 9. Out of scope

- [ ] 9.1 Static CI for this repository — `terraform fmt`/`validate`/`tflint`,
  `validate-config.py`, pytest. Tracked as #52. No secret requirement, so it should land
  independently of this change.
