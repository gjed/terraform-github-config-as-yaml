## 1. Authentication and backend documentation

- [ ] 1.1 Write `ci/docs/authentication.md` (App versus PAT, permissions per feature, passing `GITHUB_TOKEN`, no
  token in logs)
- [ ] 1.2 Add `ci/backends/` examples for S3, GCS, Azure and Terraform Cloud

## 2. GitHub Actions templates

- [ ] 2.1 Add `ci/github-actions/terraform-pr.yml` (validate, plan, upserted plan comment)
- [ ] 2.2 Add `ci/github-actions/terraform-apply.yml` (environment approval, concurrency, repository destroy guard)
- [ ] 2.3 Add `ci/github-actions/terraform-drift.yml` (schedule, calls `scripts/detect-drift.sh`, job summary)

## 3. Jenkins template

- [ ] 3.1 Add `ci/jenkins/Jenkinsfile` with placeholders for every site-specific value

## 4. Tests and documentation

- [ ] 4.1 Add `tests/test_ci_examples.py`
- [ ] 4.2 Write `ci/README.md`
- [ ] 4.3 Link the examples from `README.md`, `AGENTS.md` and `examples/consumer/README.md` (drift workflow linked,
  not copied)
- [ ] 4.4 Run pytest, pre-commit and actionlint
