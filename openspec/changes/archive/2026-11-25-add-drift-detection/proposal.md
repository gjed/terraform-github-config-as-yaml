## Why

Repositories managed by this module can be changed out of band (GitHub UI, `gh`, other API clients,
GitHub Apps), silently weakening security settings. Today the only way to notice is to run
`terraform plan` and read it by hand, and nothing separates a harmless description tweak from a
repository that is about to be destroyed or made public. Issue #9 asks for drift tooling; this change
delivers the CLI and reporting part so a scheduled CI job (added separately) can call it.

## What Changes

- Add `scripts/detect-drift.sh`: runs a full-refresh `terraform plan -detailed-exitcode`, converts the
  saved plan with `terraform show -json`, and hands it to the report helper. Exit codes: `0` no drift,
  `1` error, `2` drift, `3` critical drift (a `github_repository` would be destroyed or replaced).
- Add `scripts/drift_report.py` (Python stdlib only): reads plan JSON, ignores `no-op`/`read`, groups
  resource changes by repository, flags critical changes, masks sensitive values, and renders text
  (coloured on a TTY), markdown, or JSON.
- Add `make drift-check` (`REPO=` and `FORMAT=` optional).
- Document the workflow in `AGENTS.md` and `README.md`.
- Add pytest coverage driven by committed fixture plan JSON files under `tests/fixtures/`.

Not included: Slack/email notifications, auto-remediation, a `drift_detection:` block in
`config/config.yml`, auto-created GitHub issues, and any CI workflow or Jenkinsfile (a follow-up change
adds those and calls the script).

## Capabilities

### New Capabilities

- `drift-detection`: A CI-agnostic command that plans with a full refresh, categorises the resulting
  changes, flags critical and security-weakening changes, and reports in text, markdown, or JSON with a
  stable exit-code contract.

### Modified Capabilities

None.

## Impact

- New: `scripts/detect-drift.sh`, `scripts/drift_report.py`, `tests/test_drift_report.py`,
  `tests/test_detect_drift.py`, `tests/fixtures/drift/*.json`.
- Changed: `Makefile` (`drift-check` target, `.PHONY`, `help`), `AGENTS.md`, `README.md`,
  `.gitignore` (drift plan file).
- No Terraform, module-interface, or configuration-schema changes; no new dependencies (the helper uses
  the standard library, the script needs `terraform` and `python3`).
