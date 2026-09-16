## REMOVED Requirements

### Requirement: Repository Partitions Variable

**Reason**: The variable cannot fulfil its stated purpose ("limit which repositories are managed
in a given Terraform run") — doing so against a shared state plans destruction of every
out-of-partition repository (#71). Removed as a breaking change.
**Migration**: Remove the `repository_partitions` argument from module calls; all
`config/repository/` subdirectories are always loaded.
