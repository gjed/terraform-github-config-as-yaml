## 1. Report helper

- [ ] 1.1 Add `scripts/drift_report.py`: parse plan JSON, classify changes, group by repository
- [ ] 1.2 Flag critical changes (repository destroy/replace, security weakening) and mask sensitive values
- [ ] 1.3 Render text, markdown, and JSON; exit `0`/`2`/`3`, or `1` on invalid input

## 2. Driver script and make target

- [ ] 2.1 Add `scripts/detect-drift.sh` with `--format`, `--plan-file`, `--repo`, and `--help`
- [ ] 2.2 Add `make drift-check` (`.PHONY`, `help`, `REPO`, `FORMAT`) and ignore the drift plan file

## 3. Tests

- [ ] 3.1 Add fixture plan JSON files under `tests/fixtures/drift/`
- [ ] 3.2 Add `tests/test_drift_report.py` covering categories, critical flags, masking, and formats
- [ ] 3.3 Add `tests/test_detect_drift.py` covering exit-code pass-through with a stub `terraform`

## 4. Documentation

- [ ] 4.1 Add a "Detecting drift" section to `AGENTS.md`
- [ ] 4.2 Add drift detection to `README.md`

## 5. Verification

- [ ] 5.1 `terraform fmt -check -recursive`, `pytest tests/`, `python scripts/validate-config.py`,
      `shellcheck scripts/detect-drift.sh`, `pre-commit run --all-files`
- [ ] 5.2 Archive the change with `openspec archive add-drift-detection`
