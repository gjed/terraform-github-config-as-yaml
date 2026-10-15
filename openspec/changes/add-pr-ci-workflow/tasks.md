## 1. Prerequisite: clear baseline hook failures (separate PR, merges first)

- [ ] 1.1 Strip trailing whitespace in the archived e2e-test-fixture design doc
- [ ] 1.2 Add `pragma: allowlist secret` to the two `detect-secrets` false positives under `tests/e2e/`
- [ ] 1.3 Add `checkov:skip` (with reason) for `CKV_SECRET_6` in the webhook fixture and `CKV_GHA_7` in `e2e.yml`
- [ ] 1.4 Fix markdownlint errors in `openspec/` and `docs/RESEARCH.md` (formatting only, wording unchanged)
- [ ] 1.5 Verify `pre-commit run --all-files` exits 0 on a clean checkout

## 2. CI workflow

- [ ] 2.1 Add `.github/workflows/ci.yml` with triggers, `permissions: contents: read`, and PR-only cancel-in-progress
  concurrency
- [ ] 2.2 Add `pre-commit` job: checkout, setup-python 3.14 (pip cache), setup-terraform (no wrapper), setup-tflint,
  `pip install -r requirements.txt`, pre-commit cache, `pre-commit run --all-files --show-diff-on-failure`
- [ ] 2.3 Add `pytest` job: checkout, setup-python 3.14 (pip cache), install requirements,
  `pytest tests/ --ignore=tests/e2e`
- [ ] 2.4 Confirm action versions match those used in `e2e.yml`
- [ ] 2.5 Open a PR and confirm both jobs are green, then confirm they are green on `main` after merge

## 3. Documentation and follow-up

- [ ] 3.1 Document the CI gate and the stable check names in `CONTRIBUTING.md`
- [ ] 3.2 Open an issue or PR in the separate Terraform repository to require `pre-commit` and `pytest` on `main`
- [ ] 3.3 Comment on #52 summarizing what shipped and what moved out of scope, then close it
