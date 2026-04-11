# Change: Add Organization-Level Rulesets

Resolves: [#29](https://github.com/gjed/terraform-github-config-as-yaml/issues/29)

## Why

The module currently only supports **repository-level rulesets** (`github_repository_ruleset`), which
must be configured individually per repository. GitHub also supports **organization-level rulesets**
(`github_organization_ruleset`) that apply rules across multiple repositories based on repository
name patterns — without configuring each repo individually.

This is a significant operational advantage for organizations that want consistent policies across
many repos (e.g., "all public repos must require PR reviews") without adding a ruleset entry to each
repository's configuration.

## What Changes

- Add a new `scope: organization` field in ruleset YAML config to distinguish org-level rulesets
  from the existing repository-level rulesets
- Add support for `repository_name` conditions in org rulesets (include/exclude patterns)
- Create a new `github_organization_ruleset` Terraform resource in `main.tf` (not in the repository
  module, since org rulesets are organization-scoped, not repository-scoped)
- Extend subscription tier filtering to gate org rulesets behind `team` or `enterprise` plans
- Support the same rule types as repository rulesets (deletion, non_fast_forward, pull_request, etc.)
- Support bypass actors (same structure as repository rulesets)

## What Does NOT Change

- Existing repository-level ruleset behavior is unchanged (no `scope` field defaults to `repository`)
- The `config/ruleset/` directory structure is reused — org rulesets coexist with repo rulesets in
  the same files using the `scope: organization` field to differentiate
- All existing rule types remain supported

## YAML Config Example

```yaml
# config/ruleset/org-rulesets.yml
org-main-protection:
  scope: organization          # Required: marks this as an org-level ruleset
  target: branch
  enforcement: active
  conditions:
    ref_name:
      include: ["~DEFAULT_BRANCH"]
      exclude: []
    repository_name:           # Org-level only: which repos this applies to
      include: ["*"]
      exclude: ["sandbox-*", "test-*"]
  bypass_actors:
    - actor_type: Team
      actor_id: 12345          # Team node ID
      bypass_mode: always
  rules:
    - type: deletion
    - type: non_fast_forward
    - type: pull_request
      parameters:
        required_approving_review_count: 1
        dismiss_stale_reviews_on_push: true
```

## Impact

- Affected specs: `repository-management` (new requirement added)
- Affected code:
  - `yaml-config.tf` — separate org rulesets from repo rulesets during parsing
  - `main.tf` — new `github_organization_ruleset` resource block
- New config example: `config/ruleset/` (existing directory, new `scope` field)
- Backward compatible: existing ruleset definitions without `scope` continue to work as
  repository-level rulesets
- Subscription gating: org rulesets require `team` or `enterprise` plan (skipped with warning on
  `free`/`pro`)
