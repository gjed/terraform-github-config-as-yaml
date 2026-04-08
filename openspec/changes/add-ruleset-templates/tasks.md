## Prerequisites

- [ ] 0.1 Ensure `add-split-config-files` is implemented (provides `config/ruleset/` directory support)

## 1. Implementation

- [ ] 1.1 Create `config/ruleset/templates.yml` with default templates
- [ ] 1.2 Add local to load ruleset templates from `config/ruleset/templates.yml`
- [ ] 1.3 Implement template resolution logic (detect `template:` key in ruleset entries)
- [ ] 1.4 Implement template override merging (inline settings override template)
- [ ] 1.5 Add validation for missing template references
- [ ] 1.6 Update `merged_rulesets` local to handle both templates and custom rulesets

## 2. Default Templates

- [ ] 2.1 Define `strict-main` template (2 approvers, code owner review, linear history)
- [ ] 2.2 Define `relaxed-dev` template (1 approver, dev/develop branches)
- [ ] 2.3 Define `release-tags` template (tag protection for v\* tags)

## 3. Documentation

- [ ] 3.1 Update `docs/CONFIGURATION.md` with template usage examples
- [ ] 3.2 Document available default templates
- [ ] 3.3 Add examples of template overrides

## 4. Validation

- [ ] 4.1 Test template reference resolution
- [ ] 4.2 Test template override merging
- [ ] 4.3 Test mixed templates and custom rulesets
- [ ] 4.4 Test error handling for missing templates
- [ ] 4.5 Run `terraform validate` and `terraform plan`
