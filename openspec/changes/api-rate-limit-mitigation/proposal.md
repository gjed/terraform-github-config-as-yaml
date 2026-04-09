## Why

When managing 400+ repositories, a single `terraform plan` can exceed GitHub's API rate limit (5,000 requests/hour for PATs, 15,000 for GitHub App tokens). Each repository generates ~7 API calls during refresh (1 repo + teams + collaborators + rulesets + actions + webhooks). At 700 repos with PAT auth, you hit the wall. The module currently loads all repository configuration every run with no way to scope operations to a subset.

## What Changes

- Add repository partitioning via subdirectories under `config/repository/` and a `repository_partitions` variable to select which partitions to load
- Add a CI helper script that detects which partitions need a plan based on git diff analysis
- Add scaling documentation in `docs/` covering API cost analysis, rate limit thresholds, provider tuning, and partitioning strategy

## Capabilities

### New Capabilities

- `repository-partitioning`: Subdirectory-based partitioning of repository config files with variable-driven selection. Top-level files always load; subdirectories are selectable partitions. Backward-compatible default (empty list = all).
- `partition-detection`: CI helper script that analyzes git diff to determine which partitions (if any) need a Terraform plan run. Shared config changes trigger all partitions; partition-specific changes trigger only those partitions.
- `scaling-documentation`: Documentation covering resource-per-repo API cost breakdown, rate limit thresholds by org size, provider tuning recommendations, and partitioning strategy with CI integration examples.

### Modified Capabilities

- `module-interface`: New `repository_partitions` variable added to the module interface. Existing `config_path` behavior unchanged.

## Impact

- **`yaml-config.tf`**: File loading logic changes from flat `fileset()` to partition-aware loading. All downstream locals unchanged.
- **`variables.tf`**: New `repository_partitions` variable.
- **`modules/repository/`**: No changes.
- **`config/repository/`**: Supports new subdirectory layout (backward-compatible — flat files still work).
- **`scripts/`**: New `detect-partitions.sh` script.
- **`docs/`**: New scaling documentation.
- **Consumer example**: Updated to show partitioning usage.
- **Breaking**: None. Default behavior (empty partitions list) is identical to current behavior.
