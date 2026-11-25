## Context

This module manages GitHub organization repositories via YAML configuration. It already handles repository settings,
rulesets, webhooks, branch protections, teams, collaborators, actions, secrets and variables, and repository
environments — all following a consistent pattern: YAML files in `config/<feature>/` are loaded by `yaml-config.tf`,
merged through group inheritance, normalized into a typed shape and passed to Terraform resources, with
`lifecycle.precondition` blocks guarding configurations that cannot work. Repository environments
(`repository-environments`) and secrets (`org-secrets-and-variables`, `repo-secrets-and-variables`) are the closest
precedents and this change follows them rather than introducing a new pattern.

GitHub custom properties are org-level metadata schemas that can be assigned to repositories. The Terraform GitHub
provider (locked at 6.13.0, constraint `>= 6.12.0`) provides two resources:

- `github_organization_custom_properties` — defines a property schema (`property_name`, `value_type`, `required`,
  `description`, `default_value`, `allowed_values`, `values_editable_by`)
- `github_repository_custom_property` — assigns a value to a specific property on a specific repository
  (`repository`, `property_name`, `property_type`, `property_value`, a set of strings)

The resource name is plural for the definition (`custom_properties`) and singular for the assignment; the issue text
names `github_organization_custom_property`, which does not exist in the provider.

Custom properties are a Team/Enterprise feature on GitHub. On Free/Pro tiers, the API calls will fail.

## Goals / Non-Goals

**Goals:**

- Define custom property schemas via YAML in a dedicated `config/custom-property/` directory (one property per YAML key,
  following the `config/ruleset/`, `config/webhook/` pattern)
- Assign property values to repositories via `custom_property_values:` in groups and repositories (following the merge
  pattern used by `teams:`, `collaborators:`, `secrets:`)
- Gate on subscription tier: skip all custom property resources on Free/Pro tiers and personal accounts, visibly
  (output and validator warning), never silently
- Validate that referenced property names are defined, values match the property type and allowed values, defaults are
  valid, and required properties are satisfied on every repository — in `validate-config.py` and as preconditions
- Expose outputs for managed properties and skipped properties (names only)

**Non-Goals:**

- Bulk property assignment via `github_properties_values` (the provider resource that sets values for multiple repos at
  once) — too complex for the group-merge model, adds a different resource lifecycle
- Using custom properties as org ruleset conditions — that's an enhancement to the existing org rulesets feature, not
  part of this change
- Managing properties for personal accounts (custom properties are org-only)
- The `url` value type, regular expressions and `require_explicit_values`, which the GitHub API offers but the issue and
  the pinned provider resource do not cover (`github_organization_custom_properties` has no such arguments)

## Decisions

### 1. Config location: dedicated `config/custom-property/` directory

**Decision**: Define property schemas in `config/custom-property/*.yml`, one property per top-level key in the YAML.

**Rationale**: This matches the established pattern for rulesets (`config/ruleset/`), webhooks (`config/webhook/`),
branch protections (`config/branch-protection/`), teams (`config/team/`) and secrets (`config/secret/`). Each feature
type gets its own config directory. Putting properties in `config.yml` under a `custom_properties:` key would work but
breaks the pattern and makes `config.yml` even larger (the issue sketches that form; the directory is chosen instead).

Files are loaded with the same comment-only guard as the other directories (`yaml_blank_pattern`), merged in sorted file
order with last-file-wins, and duplicate keys across files raise a `check` warning and appear in the
`duplicate_key_warnings` output.

### 2. Value assignments: `custom_property_values:` map in groups and repos

**Decision**: Add a `custom_property_values:` key (map of property_name → value) to both group and repository YAML.
Values merge using the standard override semantics: groups applied in order, repo overrides group by property name.

**Rationale**: Follows the pattern of `teams:`, `collaborators:` and `secrets:` — a map merged with later values
overriding earlier ones. Whole values replace: a repository `tags: [a]` replaces a group `tags: [x, y]` instead of
concatenating, so a repository can narrow what a group sets. The key is added to `VALID_GROUP_KEYS` in the validator.

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

### 3. Resource placement: definitions in `custom-properties.tf`, assignments in `modules/repository/`

**Decision**: `github_organization_custom_properties` goes in a new root file `custom-properties.tf` (org-level, like
`org-secrets.tf`). `github_repository_custom_property` goes inside `modules/repository/main.tf` (per-repo, like
rulesets, webhooks, environments).

**Rationale**: This matches the existing split: org-level resources live at the root, repo-level resources live in
`modules/repository/`. A separate file keeps the definition preconditions out of the 470-line `main.tf`, as
`org-secrets.tf` does for secrets.

### 4. Dependency ordering: explicit `depends_on`

**Decision**: Add `depends_on = [github_organization_custom_properties.this]` to the `module "repositories"` block to
ensure property definitions exist before any repo tries to assign values.

**Rationale**: The connection between a property definition and a property value assignment is by name string, not by
resource reference, so Terraform cannot infer the order. The module contains no data sources, so the module-level
`depends_on` does not defer any reads. It also reverses on destroy: assignments go before definitions.

### 5. Subscription tier gating: Team/Enterprise organizations only

**Decision**: Custom property resources are only created when `subscription` is `team` or `enterprise` and
`is_organization` is `true` (`custom_properties_supported`). Otherwise definitions and assignments are skipped. The
skipped definition names are exposed in `skipped_custom_properties` (a list of names, empty when nothing is skipped);
`validate-config.py` warns when definitions or assignments exist on an unsupported configuration.

**Rationale**: GitHub custom properties are a Team/Enterprise feature. The existing tier-gated features (org rulesets,
environments) compute effective resources in locals and report skipped items in outputs. The output is a plain list of
names, as the requirement states, instead of the object-or-null shape of `skipped_org_rulesets`, because the issue asks
for names only and an empty list needs no null check. Assignments are filtered out with a `for … if` expression rather
than a conditional, because values differ in shape per repository and a conditional would have to unify them with an
empty map.

### 6. Value normalization and the module interface

**Decision**: In `yaml-config.tf` every assigned value becomes a list of strings: a scalar (string, number or boolean)
becomes a one-element list, a list passes through, anything else (a map, a nested list) becomes null. The module
variable is `map(object({ value_type, allowed_values, values }))`, so each assignment carries the type and allowed
values of its definition, and `value_type` is null when the property is not defined.

**Rationale**: The provider's `property_value` is always a set of strings, while YAML users write
`environment: production`, not `environment: [production]`. The resource also needs `property_type`, which lives on the
definition, so the type is resolved once in the root module and handed to the module together with what the
preconditions need to validate the assignment. A null value is kept (instead of failing inside `tostring`) so the
precondition can report the repository and property by name.

### 7. Validation: preconditions for assignments, definition resource for cross-repository rules

**Decision**: `github_repository_custom_property` preconditions check that the property is defined, that the value has
the right shape for the type (exactly one value except `multi_select`, `true`/`false` for `true_false`) and that
select values are in `allowed_values`. `github_organization_custom_properties` preconditions check `value_type`, that
`allowed_values` is set exactly for select types, that `default_value` is valid for the type, and that a required
property without a default has a value on every managed repository. `validate-config.py` mirrors all of these as
errors.

**Rationale**: Per-assignment rules need the repository and belong on the per-repository resource; the required rule
needs every repository and belongs on the definition. Both are plan-time failures that consumers of the module get
without running the Python script, matching environments and org secrets.

### 8. Required properties and defaults

**Decision**: A property is satisfied for a repository when the effective `custom_property_values` has an entry or the
definition has a `default_value`. A required property with neither is an error naming the repository. Missing values are
an error, not the warning the first draft of this change proposed.

**Rationale**: GitHub applies a property's default to repositories without an explicit value, so a required property
with a default can never be missing, and warning-only validation would let the apply fail at the API. A hard failure at
plan time is consistent with every other precondition in the module.

## Risks / Trade-offs

**[Provider resource maturity]** → `github_organization_custom_properties` and `github_repository_custom_property` are
relatively new resources in the provider. Edge cases (e.g., renaming a property, changing type) may cause unexpected
behavior. **Mitigation**: Document that property type changes require destroy/recreate. Test with `terraform plan`
before applying.

**[Dependency race condition]** → If `depends_on` is insufficient and Terraform parallelizes definition creation with
value assignment, applies may fail intermittently. **Mitigation**: Explicit `depends_on` + documentation to
`terraform apply` again if a first run fails on a fresh setup.

**[API-only validation]** → GitHub enforces rules this change cannot reproduce offline (for example the limit of 200
allowed values or its own restrictions on `required` and `default_value` combinations). **Mitigation**: The
preconditions cover the rules the module can express; the rest fails at apply with the API's message.

**[Config directory proliferation]** → Adding yet another config directory (`config/custom-property/`) increases the
number of directories users must understand. **Mitigation**: This is consistent with the established pattern. Users who
don't need custom properties simply don't create the directory.
