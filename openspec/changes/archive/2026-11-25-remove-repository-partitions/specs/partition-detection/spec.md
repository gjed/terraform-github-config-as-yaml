## REMOVED Requirements

### Requirement: Git-based partition detection script

**Reason**: With `repository_partitions` removed there is nothing for the script's output to
select; `scripts/detect-partitions.sh` is deleted.
**Migration**: CI pipelines that used the script to pick per-partition jobs should run a single
plan with `-refresh=false` instead (see docs/scaling.md).

### Requirement: Shared config changes trigger all partitions

**Reason**: Script deleted.
**Migration**: None.

### Requirement: Top-level repository file changes do not trigger partitions

**Reason**: Script deleted.
**Migration**: None.

### Requirement: Partition-specific changes trigger only affected partitions

**Reason**: Script deleted.
**Migration**: None.

### Requirement: Terraform-friendly output format

**Reason**: Script deleted.
**Migration**: None.

### Requirement: Combined changes follow escalation rules

**Reason**: Script deleted.
**Migration**: None.

### Requirement: No config changes detected

**Reason**: Script deleted.
**Migration**: None.
