# Change: Add Ruleset Templates

Resolves: [#2](https://github.com/gjed/github-as-yaml/issues/2)

Depends on: `add-split-config-files` (for `config/ruleset/` directory support)

## Why

Users must define complete ruleset configurations even for common patterns like "protect main branch" or
"require PR reviews". This causes repetitive configuration, potential inconsistencies, and a steeper
learning curve for new users.

## What Changes

- Add pre-built ruleset templates that users can reference by name
- Templates defined in `config/ruleset/templates.yml` (inside the ruleset directory)
- Repositories/groups can reference templates via `template: <name>` syntax
- Templates can be overridden with inline customizations
- Ship default templates for common patterns: `strict-main`, `relaxed-dev`, `release-tags`

## Impact

- Affected specs: `repository-management`
- Affected code: `terraform/yaml-config.tf` (template resolution logic)
- New file: `config/ruleset/templates.yml` (template definitions)
- Backward compatible: existing ruleset definitions continue to work
