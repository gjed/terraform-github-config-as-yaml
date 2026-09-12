## 1. Add the comment-only guard

- [x] 1.1 Add `local.yaml_blank_pattern` matching whole-line comments and blank lines
- [x] 1.2 Add `*_files_raw` maps so each file is read once
- [x] 1.3 Decode to `null` when stripping comments and blank lines leaves nothing
- [x] 1.4 Apply to `repository/`, `group/`, `ruleset/`, `membership/`, `branch-protection/`
- [x] 1.5 Leave `config.yml` unguarded — required file, empty document is an error either way

## 2. Remove duplicate file reads

- [x] 2.1 Derive `repos_config` from `repository_configs_by_file`
- [x] 2.2 Derive `groups_config` from `group_configs_by_file`
- [x] 2.3 Derive `rulesets_config` from `ruleset_configs_by_file`
- [x] 2.4 Derive `branch_protections_config` from `branch_protection_configs_by_file`
- [x] 2.5 Seed `membership_config` merge with `{}` for the empty-directory case

## 3. Verify

- [x] 3.1 `terraform validate` passes
- [x] 3.2 Comment-only file in every config directory decodes without error
- [x] 3.3 Empty (zero-byte) file decodes without error
- [x] 3.4 Invalid YAML still fails loudly with its original parse error
- [x] 3.5 `#` inside a quoted value is not treated as a comment
- [x] 3.6 The e2e fixture plan no longer aborts on `yamldecode`
- [x] 3.7 pytest suite passes
- [x] 3.8 `openspec validate fix-yamldecode-comment-only-yaml --strict` passes

## 4. Verification evidence

Against a synthetic config with a comment-only file in every directory, plus one zero-byte
file, alongside real content:

```text
local.repos_config                 ["real-repo"]
local.groups_config                ["base"]
local.rulesets_config              ["a-rs"]
local.membership_config            []
local.branch_protections_config    ["a-bp"]
```

Negative tests:

- `foo: bar\n  bad: indent` still raises
  `Call to function "yamldecode" failed: on line 2, column 1: mapping values are ...`
- `description: "value # not a comment"` decodes to `value # not a comment`, unmodified

Before this change, `terraform plan` in `tests/e2e` aborted with
`Call to function "yamldecode" failed: on line 12, column 1: missing start of document`.
After it, that error is gone and only the expected credential failure remains.

## 5. Out of scope

- [ ] 5.1 `webhook/` and `team/` still use `try(yamldecode(...), {})`, which also swallows
      malformed YAML. Narrowing them to the same strict treatment changes failure behaviour
      for invalid files and belongs in its own change.
