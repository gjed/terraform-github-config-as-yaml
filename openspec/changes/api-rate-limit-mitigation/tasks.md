## 1. Module interface

- [ ] 1.1 Add `repository_partitions` variable to `variables.tf` with type `list(string)`, default `[]`, and description
- [ ] 1.2 Run `terraform fmt` and `terraform validate` to confirm syntax

## 2. Partition-aware file loading

- [ ] 2.1 Add `repository_partition_dirs` local to discover subdirectories under `config/repository/`
- [ ] 2.2 Add `active_partitions` local that resolves empty list to all discovered partitions
- [ ] 2.3 Replace `repository_files` local with partition-aware loading (top-level `*.yml` always + active partition `*.yml`)
- [ ] 2.4 Add `check "valid_partitions"` block to validate requested partition names exist as directories
- [ ] 2.5 Verify duplicate detection still works across partition files (filenames include partition prefix)
- [ ] 2.6 Run `terraform validate` with the example consumer config to confirm backward compatibility

## 3. Partition detection script

- [ ] 3.1 Create `scripts/detect-partitions.sh` with git diff range argument parsing
- [ ] 3.2 Implement shared config detection (group/, ruleset/, webhook/, config.yml → all partitions)
- [ ] 3.3 Implement top-level repo file detection (config/repository/*.yml → no partitions)
- [ ] 3.4 Implement partition-specific detection (config/repository/<partition>/ → those partitions only)
- [ ] 3.5 Implement escalation logic (shared config overrides partition-specific)
- [ ] 3.6 Add `--tfvar` flag for JSON array output format
- [ ] 3.7 Handle no-config-changes case (empty output, exit 0)
- [ ] 3.8 Make script executable and add usage help (`--help`)

## 4. Scaling documentation

- [ ] 4.1 Create `docs/scaling.md` with resource-per-repository API cost table
- [ ] 4.2 Add rate limit threshold table (100/500/1000/2000 repos vs PAT/App limits)
- [ ] 4.3 Add provider tuning recommendations by org size (read_delay_ms, write_delay_ms)
- [ ] 4.4 Add partitioning strategy section with directory layout example
- [ ] 4.5 Add CI integration example showing `detect-partitions.sh` + `terraform plan` pipeline
- [ ] 4.6 Add warning about partition switching causing destroy plans for repos outside the selected partitions

## 5. Consumer example update

- [ ] 5.1 Update `examples/consumer/main.tf` to document `repository_partitions` usage in comments
- [ ] 5.2 Add partition warning comment about repos dropping out of scope when filtering

## 6. Validation

- [ ] 6.1 Run `terraform fmt` on all changed `.tf` files
- [ ] 6.2 Run `terraform validate` with default (empty) partitions to confirm backward compatibility
- [ ] 6.3 Run `pre-commit run --all-files` to catch linting issues
- [ ] 6.4 Test `detect-partitions.sh` manually against a sample git diff
