## Why

GitHub custom properties allow organizations to attach structured metadata to repositories — environment, compliance level, team ownership, deprecation status, etc. This metadata is useful for categorization, compliance tracking, and (critically) targeting org rulesets by property values. Today this module has no way to manage custom properties, forcing users to configure them manually outside Terraform and breaking the "config as YAML" promise.

## What Changes

- Add support for **defining custom property schemas** at the organization level via `github_organization_custom_properties` resources, configured in YAML under `config/config.yml` or a new `config/custom-property/` directory
- Add support for **assigning custom property values** to repositories via `github_repository_custom_property` resources, configurable per-group and per-repo in YAML (with the standard group-merge + repo-override inheritance)
- Add subscription tier gating: custom properties require Team or Enterprise subscription; skip gracefully on Free/Pro tiers (matching existing patterns for org rulesets, security managers)
- Add validation: referenced property names must be defined, select-type values must be in the allowed set, required properties must have values assigned
- Extend the validation script, outputs, and AGENTS.md documentation

## Capabilities

### New Capabilities

- `custom-property-definitions`: Organization-level custom property schema management (name, type, required, default, allowed values, editability)
- `custom-property-assignments`: Per-repository custom property value assignment with group inheritance and repo-level overrides

### Modified Capabilities

_(none — no existing spec-level requirements change)_

## Impact

- **New config directory**: `config/custom-property/` (or inline in `config.yml` under `custom_properties:`)
- **yaml-config.tf**: New locals for loading, merging, and validating custom property definitions and assignments
- **main.tf**: New `github_organization_custom_properties` resource block; new `github_repository_custom_property` resources (likely inside or alongside `modules/repository/`)
- **modules/repository/**: New `custom_property_values` variable and corresponding `github_repository_custom_property` resources
- **variables.tf / outputs.tf**: New outputs for managed properties and any skipped-tier warnings
- **scripts/validate-config.py**: Validation rules for property definitions and value assignments
- **AGENTS.md / README.md**: Documentation for the new feature
- **Dependency ordering**: Property definitions must be created before repo assignments (Terraform handles this via `depends_on` or implicit reference)
- **Provider constraint**: Uses existing `integrations/github ~> 6.0` — both resources are available in current provider versions
