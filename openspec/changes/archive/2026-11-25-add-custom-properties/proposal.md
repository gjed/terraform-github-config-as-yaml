## Why

GitHub custom properties allow organizations to attach structured metadata to repositories — environment, compliance
level, team ownership, deprecation status, etc. This metadata is useful for categorization, compliance tracking, and
(critically) targeting org rulesets by property values. Today this module has no way to manage custom properties,
forcing users to configure them manually outside Terraform and breaking the "config as YAML" promise.

## What Changes

- Add support for **defining custom property schemas** at the organization level via
  `github_organization_custom_properties` resources, configured in a new `config/custom-property/` directory
- Add support for **assigning custom property values** to repositories via `github_repository_custom_property`
  resources, configurable per-group and per-repo in YAML (with the standard group-merge + repo-override inheritance)
- Add account type gating: custom properties are organization-only and work on every subscription tier; for personal
  accounts definitions and assignments are skipped and reported in a `skipped_custom_properties` output and a
  `validate-config.py` warning (matching org rulesets and environments)
- Add validation, in `validate-config.py` and mirrored as Terraform preconditions for module consumers: referenced
  property names must be defined, values must match the property's type and `allowed_values`, defaults must be valid,
  and a required property without a default must have a value on every repository
- Extend outputs with `managed_custom_properties` and `skipped_custom_properties` (names only), the offline
  `terraform test` suite, the e2e fixture and AGENTS.md / README.md documentation

## Capabilities

### New Capabilities

- `custom-property-definitions`: Organization-level custom property schema management (name, type, required, default,
  allowed values, editability)
- `custom-property-assignments`: Per-repository custom property value assignment with group inheritance and repo-level overrides

### Modified Capabilities

(none — no existing spec-level requirements change)

## Impact

- **New config directory**: `config/custom-property/` (one property per top-level key, optional directory)
- **yaml-config.tf**: New locals for loading the definitions (with duplicate detection), merging and normalizing
  `custom_property_values`, and account type gating
- **custom-properties.tf** (new, like `org-secrets.tf`): `github_organization_custom_properties` resource with
  preconditions for the definitions and for required properties
- **main.tf**: `module "repositories"` receives `custom_property_values` and depends on the definitions
- **modules/repository/**: New `custom_property_values` variable and `github_repository_custom_property` resource with
  preconditions for the assigned values
- **outputs.tf**: `managed_custom_properties`, `skipped_custom_properties`, and custom property keys in
  `duplicate_key_warnings`
- **scripts/validate-config.py**: `custom_property_values` group/repository key, definition and assignment validators
  and a personal-account warning
- **tests/**: pytest suite, offline `terraform test` suite with fixtures, e2e fixture and `verify_e2e.py` checks
- **AGENTS.md / README.md**: Documentation for the new feature
- **Provider constraint**: Uses the existing `integrations/github >= 6.12.0` constraint; both resources exist in the
  locked 6.13.0 provider (`property_value` is a set of strings, `default_value` a string)
