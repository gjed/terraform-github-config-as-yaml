## REMOVED Requirements

### Requirement: Partition selection via variable

**Reason**: `repository_partitions` cannot safely scope a plan in a single state (narrowing plans
destruction of every out-of-partition repo, #71), and its only sound deployment (one state per
partition) is strictly worse than the documented `-refresh=false` pattern.
**Migration**: Delete the `repository_partitions` argument from module calls. All subdirectories
under `config/repository/` are now always loaded. Multi-state sharding users must split
`config/repository/` per root module instead.

### Requirement: Partition name validation

**Reason**: No selection variable remains to validate.
**Migration**: None; subdirectory names are no longer referenced anywhere.

### Requirement: Partition narrowing warning

**Reason**: The narrowing condition no longer exists.
**Migration**: None.

### Requirement: Subdirectory-based repository partitioning

**Reason**: Loading behavior survives but is no longer a "partitioning" capability; it moves to
`repository-management` as always-on one-level subdirectory organization.
**Migration**: None; loading behavior is unchanged when `repository_partitions` was `[]`.

### Requirement: Top-level files always loaded

**Reason**: Moved to `repository-management` (merged into the subdirectory-organization
requirement).
**Migration**: None.

### Requirement: Duplicate detection across partitions

**Reason**: Moved to `repository-management` (duplicate detection across subdirectories).
**Migration**: None.
