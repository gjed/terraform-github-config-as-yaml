## Prerequisites

- [x] 0.1 Ensure `add-split-config-files` is implemented (provides `config/ruleset/` directory support)

## 1. Implementation

- [x] 1.1 Ship default templates in `config/ruleset/default-rulesets.yml` (templates and default
  rulesets share one file rather than a separate `templates.yml`)
- [x] 1.2 Add `local.ruleset_templates` to load definitions usable as templates
- [x] 1.3 Implement template resolution logic (detect `template:` key in ruleset entries)
- [x] 1.4 Implement template override merging (inline settings override template, `template` key excluded)
- [x] 1.5 Add validation for missing template references (`check "template_references"`)
- [x] 1.6 Update `merged_rulesets` local to handle both templates and direct references, keying
  resolved templates as `tpl-<name>-<idx>` to avoid collisions

## 2. Default Templates

- [x] 2.1 Define `strict-main` template (2 approvers, code owner review, linear history)
- [x] 2.2 Define `relaxed-devel` template (1 approver, `refs/heads/devel`)
- [x] 2.3 Define `tag-protection` template (tag protection for `refs/tags/v*`)

## 3. Documentation

- [x] 3.1 Document template usage with examples (`wiki/Configuration-Reference.md`, `wiki/Examples.md`)
- [x] 3.2 Document available default templates and default rulesets
- [x] 3.3 Document template override semantics (overrides replace the whole section)

## 4. Validation

- [x] 4.1 Test template reference resolution
- [x] 4.2 Test template override merging
- [x] 4.3 Test mixed templates and direct ruleset references
- [x] 4.4 Test error handling for missing templates
- [x] 4.5 Run `terraform validate` and `terraform plan`

## Notes

Delivered by PR #16 (`feat(rulesets): consolidate templates and add OSS bypass ruleset`),
which closed issue #2 on 2026-01-21. Task wording above was corrected during archival to
match the shipped implementation:

- templates live in `config/ruleset/default-rulesets.yml`, not a separate `templates.yml`
- the devel template is named `relaxed-devel`, not `relaxed-dev`
- the tag template is named `tag-protection`, not `release-tags`
- documentation landed in `wiki/`, not `docs/CONFIGURATION.md`
