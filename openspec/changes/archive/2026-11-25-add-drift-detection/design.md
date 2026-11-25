## Context

Issue #9 proposes drift tooling. The reference is a nightly drift run in a downstream infra repo: the
plan always refreshes (PR and merge plans may skip it), changes are detected from the plan JSON, and a
plan that destroys or replaces a `github_repository` is a hard failure. This change reproduces that
logic as a CI-agnostic script, leaving the CI wiring to a later change.

## Goals / Non-Goals

**Goals:**

- A single command usable from a terminal, `make`, and any CI runner.
- Categorised, security-aware output with sensitive values masked.
- A stable exit-code contract.

**Non-Goals:**

- Notifications, auto-remediation, auto-created issues, a `drift_detection:` config block, CI workflows.
- Comparing GitHub state to YAML directly through the GitHub API. Terraform's refresh already does that
  for every managed resource.

## Decisions

### Decision 1: Terraform plan as the drift source

**Choice:** `terraform plan -detailed-exitcode -out=FILE`, then `terraform show -json FILE`.

**Rationale:** The provider refresh is the only comparison that covers every managed attribute. The
issue's `Repository: ... DRIFT:` example is reproduced by the report, not by a second API client.

### Decision 2: Split bash driver and Python helper

**Choice:** `scripts/detect-drift.sh` orchestrates Terraform; `scripts/drift_report.py` is a stdlib-only
parser that reads plan JSON from a file or stdin.

**Rationale:** The parser holds all the logic worth testing and runs against fixture JSON without
Terraform or credentials. Python is already used by `scripts/validate-config.py`; no `jq` dependency.

### Decision 3: Exit codes come from the plan JSON, with `3` for critical

**Choice:** `0` no resource changes, `2` changes, `3` repository destroy/replace, `1` error. The
Terraform exit status only distinguishes success from error.

**Rationale:** `-detailed-exitcode` returns `2` for output-only changes, which are not drift. The
reference reads the JSON for the same reason. A distinct code for repository destroy/replace lets CI
treat it as a hard failure without parsing output. Security-weakening changes are flagged critical in the
report but exit `2`, so only repository destruction blocks.

### Decision 4: Direction of "security-weakening"

**Choice:** A change is security-weakening when applying the plan would weaken a setting (for example
`before.visibility = private`, `after.visibility = public`). The opposite direction, where GitHub already
holds the weaker value and the plan restores the stronger one, shows as an ordinary update with its
before and after values.

**Rationale:** It matches the plan's own semantics and the wording of the requirement. Treating each
create as "protection missing on GitHub" would mislabel every newly configured ruleset.

### Decision 5: Sensitive values

**Choice:** `terraform show -json` carries sensitive values in clear text next to `before_sensitive` and
`after_sensitive` masks. The helper compares values, then renders any attribute under a mask as
`(sensitive)`; attributes unknown until apply are rendered as `(known after apply)`.

**Rationale:** Never leak secrets into CI logs or PR comments. The plan file itself still holds the
values, which is why a kept `--plan-file` must be treated as a secret.

### Decision 6: Plan file handling

**Choice:** Without `--plan-file` the plan goes to a temporary file removed on exit; with it, the file
is kept for the caller. Default is not `tfplan`, so a saved `make plan` is never overwritten.

**Rationale:** Plan files can contain secrets; keep them only when asked.

## Risks / Trade-offs

- Full refresh costs about ten API reads per repository, so large organisations should run it on a
  schedule, not on every PR. This is why the command never passes `-refresh=false`.
- `terraform show -json` output evolves with Terraform versions; the helper only reads
  `resource_changes[].{address,module_address,type,change.{actions,before,after,*_sensitive,after_unknown}}`,
  which has been stable since format version 0.2.
- A kept plan file contains sensitive values in clear text. Callers that pass `--plan-file` own that
  file's confidentiality.
