## Why

`config/group/default-groups.yml` ships `require_linear_history: true` on the `oss` group. The module never
reads that key, and GitHub has no repository-level linear-history setting, so the key is silently ignored.
Consumers copy it, see it in `show-repo-config.py` output, and conclude it is enforced (observed in
zextras/infra-github-config#142).

`validate-config.py` let it survive: it only checks unknown keys in `config.yml` (`security:`, `settings:`).
Group and repository entries have no key allowlist, so any typo'd, invented, or obsolete key passes validation
and is then dropped by `yaml-config.tf`. Same failure class as #63 (configuration accepted, then silently
discarded). Tracked in #84.

## What Changes

- Remove the dead `require_linear_history: true` key from the `oss` group in
  `config/group/default-groups.yml`. Linear history is enforced by the `required_linear_history` rule type in
  rulesets or by `required_linear_history` in branch protections.
- `validate-config.py` warns on unknown keys in group entries (`VALID_GROUP_KEYS`) and repository entries
  (`VALID_REPOSITORY_KEYS`), derived from the keys `yaml-config.tf` reads. Unknown keys are **warnings**, not
  errors, so existing consumer configs do not break on upgrade. A dedicated message is emitted for
  `require_linear_history`.
- Document in `docs/CONFIGURATION.md` that linear history is branch-level only.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-management`: adds a requirement that unknown keys in group and repository entries are reported
  as validation warnings.

## Impact

- `config/group/default-groups.yml` — remove one line
- `scripts/validate-config.py` — `VALID_GROUP_KEYS`, `VALID_REPOSITORY_KEYS`, unknown-key warnings
- `tests/` — validator unit tests
- `docs/CONFIGURATION.md` — linear-history note
- Not breaking: unknown keys produce warnings only. Dropping the dead key changes no Terraform behavior.
