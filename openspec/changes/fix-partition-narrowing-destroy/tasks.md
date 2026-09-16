## 1. Module guard

- [ ] 1.1 Add `check "partition_narrowing"` to `yaml-config.tf` — warn when
  `0 < length(var.repository_partitions) < length(local.repository_partition_dirs)`
- [ ] 1.2 Rewrite `repository_partitions` description in `variables.tf` to document the
  static state-sharding contract and the destroy-on-narrow risk against a shared state

## 2. Partition detection retargeting

- [ ] 2.1 Update `scripts/detect-partitions.sh` header comment and `--help` text to describe
  selecting per-partition root modules/CI jobs, not a shared-state `TF_VAR`
- [ ] 2.2 No change to the script's classification/escalation logic or `--tfvar` output format

## 3. Documentation rewrite

- [ ] 3.1 Add a "Reducing plan cost with `-refresh=false`" section to `docs/scaling.md` as the
  primary scaling guidance, including the scheduled full-refresh drift-plan pattern
- [ ] 3.2 Rewrite the "Repository Partitioning" section: state-sharding contract, per-partition
  root module + backend example, replacing the single-state Actions example
- [ ] 3.3 Delete the `TF_VAR_repository_partitions`-from-git-diff single-state Actions example
- [ ] 3.4 Fix the warning box that currently points at #37 deletion protection as a safety net —
  it would deadlock, not protect; point at the state-sharding requirement instead
- [ ] 3.5 Update `examples/consumer/main.tf` partition comments to match the sharding contract

## 4. Amend pending #37 change (`protect-repos-from-deletion`, still unimplemented)

- [ ] 4.1 Remove `prevent_destroy = true` from `proposal.md`, `design.md`, and
  `specs/deletion-protection/spec.md` (including the "partition switch → plan error" scenario
  and Decision 1)
- [ ] 4.2 Rewrite `design.md` Decision 1 to explain why `prevent_destroy = true` is dropped
  (deadlocks against partition narrowing; blocks normal decommissioning)
- [ ] 4.3 Confirm `archive_on_destroy` default stays `false` in `proposal.md`/spec (no behavior
  change this release); note the default-to-`true` flip as deferred to the next major version

## 5. Spec deltas

- [ ] 5.1 `repository-partitioning`: add "Partition selection is a state-sharding mechanism"
  requirement with scenarios for dedicated-state pairing, unsupported shared-state narrowing,
  and the narrowing warning
- [ ] 5.2 `partition-detection`: retarget purpose to per-partition job/root-module selection
- [ ] 5.3 `scaling-documentation`: require `-refresh=false` as primary guidance, require the
  multi-root-module partitioning example, require the corrected warning text

## 6. Verification

- [ ] 6.1 `terraform fmt` and `terraform validate`
- [ ] 6.2 `pre-commit run --all-files`
- [ ] 6.3 Manually verify the new `check` block fires a warning (not an error) on a narrowed
  `repository_partitions` against the e2e fixture, and stays silent when empty or full
- [ ] 6.4 `openspec validate fix-partition-narrowing-destroy --strict`
