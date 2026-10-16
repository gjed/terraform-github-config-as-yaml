## Context

The repository has `release.yml` (semantic-release on push to `main`) and `e2e.yml` (nightly and manual, uses an
`e2e` environment and a token able to delete repositories). There is no PR-time workflow. `pre-commit run
--all-files` is the single definition of the quality gates. Measured on `main` at 9e4df6b: `terraform_fmt`,
`terraform_validate`, `terraform_tflint`, `yamllint`, `validate-config`, and all 70 pytest tests pass; the remaining
failures are listed under Decisions.

## Goals / Non-Goals

**Goals:**

- A PR gate that cannot drift from local hooks.
- Safe for fork PRs: no secrets, read-only token.
- Green on `main` at introduction.

**Non-Goals:**

- Required-check enforcement (lives in the separate Terraform repository that manages this repository's rulesets).
- Changes to `e2e.yml` triggers or `release.yml`.
- Adding new linters.

## Decisions

### Reuse `pre-commit run --all-files` instead of per-tool steps

One job runs the existing hooks, so adding or changing a hook updates CI automatically. Rejected: separate steps for
`terraform fmt -check`, `tflint`, `checkov`, etc. — duplicates configuration and drifts. The issue's proposed explicit
`terraform fmt -check -recursive` gate is dropped because the `terraform_fmt` hook already covers it.

### Two jobs: `pre-commit` and `pytest`

`pytest` is separate for parallelism and so a test failure is distinguishable from a lint failure. Both names are part
of the contract with the external ruleset (see spec). `pytest` runs `pytest tests/ --ignore=tests/e2e`.

### Toolchain

- `actions/checkout@v7`, `actions/setup-python@v7` with Python `3.14`, and `hashicorp/setup-terraform@v4` with
  `terraform_wrapper: false` — matching the versions already used in `e2e.yml`, which Renovate keeps current.
  Version-tag pinning (not SHA) follows the existing convention; the issue's `@v4`/`@v5` examples are outdated.
- `terraform-linters/setup-tflint` provides TFLint (the hook shells out to it).
- `pip install -r requirements.txt` provides `pre-commit`, `checkov`, and `pytest`.
- Caches: `actions/setup-python` `cache: pip`, and `actions/cache` on `~/.cache/pre-commit` keyed on
  `.pre-commit-config.yaml`.

### Permissions and triggers

`on: pull_request` and `push` to `main`; top-level `permissions: contents: read`. Concurrency uses one group per pull
request number with `cancel-in-progress` so only superseded PR runs are cancelled, and a group unique to each push run
(`github.run_id`) so pushes to `main` never cancel or replace one another. A shared per-ref group is not enough: even
with `cancel-in-progress: false`, GitHub keeps only one pending run per group, so a third push replaces the queued
second one and that commit is never checked. No `pull_request_target`, no
secrets, no environment.

### Baseline debt is cleared in a prerequisite PR, not suppressed globally

Failures found on `main`, and resolution:

| Hook | Finding | Resolution |
|---|---|---|
| `trailing-whitespace` | one line in an archived openspec design doc | strip |
| `detect-secrets` | `tests/e2e/terraform.tfvars.example`, `tests/e2e/config/webhook/test-webhooks.yml` (placeholder / env reference) | inline `pragma: allowlist secret` |
| `checkov` `CKV_SECRET_6` | same webhook fixture line | inline `checkov:skip` with reason |
| `checkov` `CKV_GHA_7` | `e2e.yml` `workflow_dispatch` input `skip_destroy` | inline `checkov:skip` with reason (debug toggle, cannot alter build output) |
| `markdownlint` | about 170 `MD013` plus assorted errors in `openspec/` and `docs/RESEARCH.md` | re-wrap and format; wording unchanged, including archived specs |

Rejected: excluding `openspec/` from markdownlint — it would hide future errors in files that agents and maintainers
edit constantly. Archived files are edited for formatting only; this deviates from the "do not edit archive" rule in
`skills/internal/openspec-workflow` and is acknowledged there.

`checkov` also warns that it cannot download the external module `gjed/config-as-yaml/github` referenced by
`examples/consumer`. It is a warning and does not fail the hook, so it is left alone.

## Risks / Trade-offs

- **Network-dependent hooks** (`terraform init` for `validate`, provider and tflint plugin downloads) can flake →
  mitigated by `--retry-once-with-cleanup`, already configured; accept occasional re-runs.
- **Slow `pre-commit`** (checkov, multiple Terraform inits) → caching; revisit splitting hooks into jobs only if runs
  exceed a few minutes.
- **Ruleset coupling**: check names are an external contract → documented as a requirement.
- **Order dependency**: if CI merges before the lint-debt PR, `main` goes red → the debt PR merges first.

## Migration Plan

1. Merge the lint-debt PR (formatting and suppressions only).
2. Merge this change's implementation PR; confirm both jobs are green on `main`.
3. In the separate Terraform repository, add `pre-commit` and `pytest` to the required status checks for `main`.

Rollback: delete `ci.yml`; nothing else depends on it until step 3.
