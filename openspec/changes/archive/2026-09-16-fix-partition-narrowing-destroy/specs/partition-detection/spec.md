## MODIFIED Requirements

### Requirement: Git-based partition detection script

The module SHALL include a script at `scripts/detect-partitions.sh` that analyzes git diff output
and outputs affected partition names. The script's output identifies which per-partition **root
modules or CI jobs** are affected by a diff, each managing its own dedicated Terraform state. The
output SHALL NOT be fed as `repository_partitions` into a `terraform plan` against a single shared
state, since doing so plans destruction of every repository outside the selected partitions.

#### Scenario: Script accepts git diff range

- **WHEN** the script is invoked as `./scripts/detect-partitions.sh main...HEAD`
- **THEN** it SHALL analyze changed files between the specified git refs

#### Scenario: Output selects per-partition CI jobs, not a shared-state plan

- **WHEN** the script outputs `["infra", "product"]` for a given diff
- **THEN** a consumer's CI SHALL run the `infra` and `product` per-partition root modules/jobs
  (each with its own state and backend)
- **AND** the output SHALL NOT be passed as `TF_VAR_repository_partitions` to a `terraform plan`
  against a state that also manages other partitions
