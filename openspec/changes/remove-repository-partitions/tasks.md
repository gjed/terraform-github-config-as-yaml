## 1. Module

- [x] 1.1 Delete `repository_partitions` variable from `variables.tf`
- [x] 1.2 `yaml-config.tf`: replace partition-aware collection with unconditional
  `fileset(local.repository_config_path, "*/*.yml")` alongside top-level files
- [x] 1.3 `yaml-config.tf`: delete `repository_partition_dirs`, `active_partitions`,
  `invalid_partition_names` locals and the `valid_partitions` / `partition_narrowing` checks

## 2. Validator and tests

- [x] 2.1 `scripts/validate-config.py`: drop `--partitions` arg, `validate_partitions()`, and the
  partition filter in `load_repository_config()` (always load one-level subdirs)
- [x] 2.2 Replace `tests/test_validate_partitions.py` with subdirectory-loading tests
  (`tests/test_load_repository_config.py`)

## 3. Scripts, docs, examples, e2e

- [x] 3.1 Delete `scripts/detect-partitions.sh`
- [x] 3.2 `docs/scaling.md`: remove Repository Partitioning + detect-partitions CI sections;
  point large orgs at `-refresh=false` + GitHub App token only
- [x] 3.3 `examples/consumer/main.tf`: replace partition comment block with a note that
  subdirectories are always loaded
- [x] 3.4 `tests/e2e/main.tf`: drop `repository_partitions`; `tests/verify_e2e.py` wording →
  subdirectory loading
- [x] 3.5 Check AGENTS.md / README / CONFIGURATION.md for stray references

## 4. Verification

- [x] 4.1 `terraform fmt` + `terraform validate`
- [x] 4.2 `pytest tests/ -k "not e2e"`
- [x] 4.3 `pre-commit run --all-files`
- [x] 4.4 `openspec validate remove-repository-partitions --strict`
