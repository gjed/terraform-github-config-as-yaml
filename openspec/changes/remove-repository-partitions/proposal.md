## Why

`repository_partitions` was shipped (#36) to cut plan-time API cost by scoping a plan to a subset
of repositories. It cannot do that: narrowing the list against a shared state removes every
out-of-partition repo's `for_each` key, so Terraform plans their **destruction** (#71). The interim
fix (v1.7.0) redefined it as a static state-sharding input and added a plan-time warning, but that
leaves a variable whose only safe use requires N root modules, N backends, and cross-backend state
surgery — while the actual scaling goal is already met by `-refresh=false` (documented as the
primary path). A selection mechanism whose misuse destroys ~100+ repositories and whose correct use
is strictly worse than the documented alternative should not exist. Rip it out.

## What Changes

- **BREAKING**: Remove the `repository_partitions` variable from the module interface. Consumers
  passing it will get an "undeclared variable" error on upgrade and must simply delete the
  argument.
- Keep one-level subdirectory loading under `config/repository/` as a pure organizational feature:
  all top-level `*.yml` files and all `*.yml` files in immediate subdirectories are **always**
  loaded. No selection, no narrowing, no destroy path.
- Remove the `valid_partitions` and `partition_narrowing` check blocks and the partition locals
  from `yaml-config.tf`.
- Remove `--partitions` support and `validate_partitions()` from `scripts/validate-config.py`;
  subdirectory-aware loading stays.
- Delete `scripts/detect-partitions.sh` (its only purpose was partition selection).
- Rewrite `docs/scaling.md`: drop the Repository Partitioning and detect-partitions CI sections;
  `-refresh=false` + scheduled full-refresh plan becomes the sole scaling guidance.
- Update `examples/consumer/main.tf` and the e2e fixture (drop `repository_partitions` argument;
  the `partitioned/` fixture directory stays to exercise subdirectory loading).

## Capabilities

### Modified Capabilities

- `repository-management`: add the always-loaded one-level subdirectory requirement (moved from
  `repository-partitioning`, stripped of selection semantics).
- `module-interface`: remove the `repository_partitions` variable requirement.
- `scaling-documentation`: remove partitioning-strategy requirements; `-refresh=false` is the only
  documented scaling mechanism.
- `e2e-test-fixture`: the subdirectory-loaded repo scenario no longer sets
  `repository_partitions`.

### Removed Capabilities

- `repository-partitioning`: selection variable, name validation, and narrowing warning all
  removed. Surviving loading behavior moves to `repository-management`.
- `partition-detection`: `scripts/detect-partitions.sh` deleted.

## Impact

- `variables.tf` — delete `repository_partitions`
- `yaml-config.tf` — always load `*/*.yml`; delete partition locals and both check blocks
- `scripts/validate-config.py` — delete `--partitions`, `validate_partitions()`; keep subdir loading
- `scripts/detect-partitions.sh` — deleted
- `tests/test_validate_partitions.py` — replaced by subdirectory-loading tests only
- `tests/e2e/main.tf`, `tests/verify_e2e.py` — drop the variable; fixture exercises subdir loading
- `docs/scaling.md`, `examples/consumer/main.tf` — partitioning content removed
- Migration for the (unsupported) multi-state sharding pattern: users must split
  `config/repository/` per root module instead of sharing one config tree with different
  partition values.
