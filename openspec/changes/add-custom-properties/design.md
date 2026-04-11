## Context

This module manages GitHub organization repositories via YAML configuration. It already handles repository settings, rulesets, webhooks, branch protections, teams, collaborators, and actions — all following a consistent pattern: YAML files in `config/<feature>/` are loaded by `yaml-config.tf`, merged through group inheritance, and passed to Terraform resources.

GitHub custom properties are org-level metadata schemas that can be assigned to repositories. The Terraform GitHub provider (`~> 6.0`) provides two resources:

- `github_organization_custom_properties` — defines a property schema (name, type, required, default, allowed values, editability)
- `github_repository_custom_property` — assigns a value to a specific property on a specific repository

Custom properties are a Team/Enterprise feature on GitHub. On Free/Pro tiers, the API calls will fail.

## Goals / Non-Goals

**Goals:**

- Define custom property schemas via YAML in a dedicated `config/custom-property/` directory (one property per YAML key, following the `config/ruleset/`, `config/webhook/` pattern)
- Assign property values to repositories via `custom_property_values:` in groups and repositories (following the merge pattern used by `teams:`, `collaborators:`, `webhooks:`)
- Gate on subscription tier: skip all custom property resources on Free/Pro tiers with a warning (matching the org rulesets and security managers patterns)
- Validate that referenced property names are defined, select-type values match allowed values, and required properties have assignments
- Expose outputs for managed properties and any skipped-tier warnings

**Non-Goals:**

- Bulk property assignment via `github_properties_values` (the provider resource that sets values for multiple repos at once) — too complex for the group-merge model, adds a different resource lifecycle
- Using custom properties as org ruleset conditions — that's an enhancement to the existing org rulesets feature, not part of this change
- Managing properties for personal accounts (custom properties are org-only)

## Decisions

### 1. Config location: dedicated `config/custom-property/` directory

**Decision**: Define property schemas in `config/custom-property/*.yml`, one property per top-level key in the YAML.

**Rationale**: This matches the established pattern for rulesets (`config/ruleset/`), webhooks (`config/webhook/`), branch protections (`config/branch-protection/`), and teams (`config/team/`). Each feature type gets its own config directory. Putting properties in `config.yml` under a `custom_properties:` key would work but breaks the pattern and makes `config.yml` even larger.

**Alternative considered**: Inline in `config.yml`. Rejected because it diverges from the directory-per-feature pattern and `config.yml` already has org-level settings, actions, security, and webhooks — adding another large block would hurt readability.

### 2. Value assignments: `custom_property_values:` map in groups and repos

**Decision**: Add a `custom_property_values:` key (map of property_name → value) to both group and repository YAML. Values merge using the standard override semantics: groups applied in order, repo overrides group.

**Rationale**: Follows the exact pattern of `teams:`, `collaborators:`, and `webhooks:` — a map that merges via `merge()` with later values overriding earlier ones. This is the most familiar UX for users of this module.

**Example**:
```yaml
# config/group/groups.yml
oss:
  custom_property_values:
    environment: production
    compliance_level: none

# config/repository/repos.yml
my-repo:
  groups: ["oss"]
  custom_property_values:
    compliance_level: soc2  # overrides group value
```

### 3. Resource placement: property definitions in `main.tf`, value assignments in `modules/repository/`

**Decision**: `github_organization_custom_properties` resources go in `main.tf` (org-level, like org rulesets, org webhooks, org settings). `github_repository_custom_property` resources go inside `modules/repository/main.tf` (per-repo, like rulesets, webhooks, branch protections).

**Rationale**: This matches the existing split: org-level resources live in the root `main.tf`, repo-level resources live in `modules/repository/`. The dependency (definitions before assignments) is handled naturally because `module "repositories"` depends on the org-level resources via Terraform's implicit ordering.

**Alternative considered**: Putting value assignments in `main.tf` outside the module using a flat `for_each` over `{ repo => { property => value } }`. Rejected because it breaks the module encapsulation and diverges from how every other per-repo feature works.

### 4. Dependency ordering: explicit `depends_on`

**Decision**: Add `depends_on = [github_organization_custom_properties.this]` to the `module "repositories"` block to ensure property definitions exist before any repo tries to assign values.

**Rationale**: While Terraform might infer the dependency from shared resource references, the connection between a property definition and a property value assignment is by name string, not by resource reference. An explicit `depends_on` prevents race conditions where Terraform tries to assign a value to a property that hasn't been created yet. This is a standard Terraform pattern for resources linked by name rather than by ID.

### 5. Subscription tier gating: Team/Enterprise only

**Decision**: Custom property resources are only created when `subscription` is `team` or `enterprise` and `is_organization` is `true`. On other tiers, all custom property resources are skipped and a warning is emitted via outputs.

**Rationale**: GitHub custom properties are a Team/Enterprise feature. The existing pattern for tier-gated features (org rulesets, security managers) uses locals to compute effective resources and outputs to surface skipped items. This follows the same approach.

### 6. Multi-select value handling

**Decision**: For `multi_select` properties, the YAML value is a list. For all other types (`string`, `single_select`, `true_false`), the value is a scalar string. The Terraform code wraps scalars in a single-element list when passing to `github_repository_custom_property.property_value` (which always expects a list).

**Rationale**: The provider's `property_value` argument is always a list, but for non-multi-select types it must be a single-element list. Handling this in the Terraform locals layer keeps the YAML ergonomic (users write `environment: production`, not `environment: [production]`).

## Risks / Trade-offs

**[Provider resource maturity]** → `github_organization_custom_properties` and `github_repository_custom_property` are relatively new resources in the provider. Edge cases (e.g., renaming a property, changing type) may cause unexpected behavior. **Mitigation**: Document that property type changes require destroy/recreate. Test with `terraform plan` before applying.

**[Dependency race condition]** → If `depends_on` is insufficient and Terraform parallelizes definition creation with value assignment, applies may fail intermittently. **Mitigation**: Explicit `depends_on` + documentation to `terraform apply` twice if a first run fails on a fresh setup.

**[Required property validation gap]** → Terraform cannot enforce at plan time that every repository has a value for every required property. The GitHub API will reject the assignment if a required property has no value, but this happens at apply time, not plan time. **Mitigation**: Python validation script checks that required properties have values in all repos. This catches issues before `terraform apply`.

**[Config directory proliferation]** → Adding yet another config directory (`config/custom-property/`) increases the number of directories users must understand. **Mitigation**: This is consistent with the established pattern. Users who don't need custom properties simply don't create the directory.
