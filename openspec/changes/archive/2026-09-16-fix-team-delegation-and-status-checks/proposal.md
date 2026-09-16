## Why

The first live run of the e2e fixture ([run 34852064683](https://github.com/gjed/terraform-github-config-as-yaml/actions/runs/34852064683))
failed at `terraform plan` with four errors. Two are module defects that affect every consumer.

### Delegation algorithm casing is inverted

`modules/team/variables.tf` validates the algorithm against `["round_robin", "load_balance"]` and
`modules/team/main.tf` defaults to `"round_robin"`. The provider accepts neither. Verified by
applying against a real organization:

```
Error: expected algorithm to be one of ["ROUND_ROBIN" "LOAD_BALANCE"], got round_robin
```

The same configuration with `ROUND_ROBIN` applies cleanly. The module therefore validates *only*
values the provider rejects, and rejects the only values it accepts. Any team that sets
`review_request_delegation` fails, whichever casing the consumer writes:

- lowercase passes module validation, then fails at the provider
- uppercase fails module validation before reaching the provider

`examples/consumer/config/team/engineering.yml` ships `algorithm: round_robin`, so the documented
example is broken for anyone who copies it. The spec's own scenarios document the same lowercase
form.

### `required_checks` defaults to null inside a typed object

`modules/repository/variables.tf` declares `required_checks` as an `optional()` attribute with no
default. Inside a typed object the attribute always exists, so
`lookup(parameters, "required_checks", [])` finds it and returns its value — `null` — rather than
the `[]` fallback. `for_each` cannot take null:

```
Error: Invalid dynamic for_each value
Cannot use a null value in for_each.
```

Any ruleset declaring a `required_status_checks` rule without listing checks fails at plan time.
The org-level path in `main.tf` reads untyped decoded YAML, where `lookup` does return the
fallback, but a key written with no value still decodes to null and hits the same error.

## What Changes

- Accept both casings for `review_request_delegation.algorithm` and normalise to the provider's
  uppercase form, so existing lowercase configurations keep working.
- Default `required_checks` to `[]` in the typed repository ruleset variable, and guard the
  org-level `for_each` against a null value from YAML.
- Correct the consumer example and the spec scenarios, which both document the rejected casing.
- Add regression tests covering algorithm casing and `member_count` bounds.

Two fixture bugs surfaced by the same run are corrected alongside: `member_count: 0` violates the
documented minimum, and one ruleset used `required_status_checks:` as the parameter key instead of
`required_checks:`.

## Impact

- Affected specs: `team-management`, `repository-management`
- Affected code: `modules/team/variables.tf`, `modules/team/main.tf`,
  `modules/repository/variables.tf`, `modules/repository/main.tf`, `main.tf`,
  `scripts/validate-config.py`, `examples/consumer/config/team/engineering.yml`
- Affected fixture: `tests/e2e/config/team/test-teams.yml`,
  `tests/e2e/config/ruleset/test-rulesets.yml`
- No breaking change: lowercase configurations continue to validate and now reach the provider in
  the form it accepts.
