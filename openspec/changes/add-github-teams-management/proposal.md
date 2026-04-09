# Change: Add GitHub Teams Management

## Why

The module manages team-to-repository assignments (`github_team_repository`) but teams themselves
must be created and managed outside the module. This forces users to either manually create teams
in the GitHub UI or maintain a separate Terraform configuration for team resources. Team definitions
are not codified, creating a gap in the GitOps workflow.

## What Changes

- **NEW**: Team creation and configuration via `github_team` resource
- **NEW**: Team membership management via `github_team_membership` resource
- **NEW**: PR review request delegation via `github_team_settings` resource
- **NEW**: `config/team/` directory for YAML-based team definitions
- **NEW**: Nested team hierarchy support (up to 3 levels deep)
- **NEW**: `modules/team/` submodule for team resource management
- **NEW**: Validation for team configuration (parent references, depth limits, required fields)
- **BREAKING**: None — this is additive functionality

## Impact

- Affected specs: `repository-management` (cross-reference validation warning for team slugs)
- New spec area: `team-management`
- Affected code:
  - `yaml-config.tf` — team config loading, flattening nested hierarchy, tier classification
  - `main.tf` — team module invocations (one per tier)
  - `modules/team/` — new submodule
  - `scripts/validate-config.py` — team schema validation
  - `config/team/` — new config directory (template examples)
  - `variables.tf` — no changes expected (teams read from config_path)
  - `outputs.tf` — team-related outputs
