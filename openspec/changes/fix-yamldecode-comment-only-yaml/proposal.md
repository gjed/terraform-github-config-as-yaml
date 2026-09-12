## Why

`yamldecode()` rejects a YAML file that contains only comments and/or blank lines with:

```text
Call to function "yamldecode" failed: on line 12, column 1: missing start of document.
```

It does not return `null` — it raises, aborting `terraform plan` before any downstream null
check can run.

The module ships exactly such a file. `config/membership/example-members.yml` is entirely
commented out by design, because membership management is opt-in and high-risk. The comment
above `local.membership_config` already anticipates the null case:

> Null entries (comment-only files) are excluded explicitly rather than via `try()`,
> so that genuinely invalid YAML still fails loudly at plan time.

That guard is correct in intent but unreachable: `yamldecode()` errors first.

Any consumer who follows the documented pattern of leaving a config file commented out hits a
hard plan failure. This affects `repository/`, `group/`, `ruleset/`, `membership/`, and
`branch-protection/`. The `webhook/` and `team/` directories already wrap their decode in
`try(..., {})`, so they do not fail — but that broad `try()` also swallows genuinely malformed
YAML, which is the behaviour the membership comment explicitly rejected.

## What Changes

- Add `local.yaml_blank_pattern`, matching whole-line comments and blank lines.
- Read each config file once into a `*_files_raw` map, and decode to `null` when stripping
  comments and blank lines leaves nothing.
- Derive the merged `*_config` locals from the existing `*_configs_by_file` maps instead of
  re-reading every file a second time, filtering nulls with an `if` clause.
- Leave `config.yml` unguarded: it is required and must define `organization`, so an empty
  document is a configuration error regardless.

Genuinely invalid YAML still reaches `yamldecode()` and still fails loudly with its original
parse error. A `#` inside a quoted value is not treated as a comment, because only whole-line
comments are stripped.

`webhook/` and `team/` keep their existing `try(..., {})` handling; narrowing those to the same
strict treatment would change failure behaviour for malformed files and belongs in its own
change.

## Impact

- Affected specs: `repository-management` (YAML-Based Repository Configuration)
- Affected code: `yaml-config.tf`
- Consumers with a fully commented-out config file: plan now succeeds instead of aborting.
- Consumers with valid config: no change. The merged maps contain exactly the same keys.
- Consumers with malformed YAML: unchanged — still a loud parse error.
- Side effect: each config file is now read once rather than twice, since the merge locals
  reuse the per-file maps that already existed for duplicate detection.
