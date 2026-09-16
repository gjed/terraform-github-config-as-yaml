## Why

The e2e fixture's first fully-configured run ([run 34852064683](https://github.com/gjed/terraform-github-config-as-yaml/actions/runs/34852064683), after the delegation-casing and status-check fixes) failed at `terraform apply` with three more errors, reproduced directly against the live GitHub API rather than inferred from docs:

```
Error: PUT https://api.github.com/repos/gjed-io/e2e-multi-group/actions/permissions/selected-actions: 409
Error: PUT https://api.github.com/repos/gjed-io/e2e-actions-restricted/actions/permissions/selected-actions: 409
Error: POST https://api.github.com/orgs/gjed-io/teams: 422 Visibility can't be secret for a child team
```

### Org-level `allowed_actions: selected` unconditionally blocks repo-level actions config

Confirmed with direct `gh api` calls against `gjed-io`, isolated from Terraform:

- Org set to `allowed_actions: selected` (matching `tests/e2e/config/config.yml`), then any repo-level `PUT .../actions/permissions/selected-actions` returns `409 Conflict` — `"Selected actions and workflows are already set at the organization or enterprise level"`.
- This holds even when the repo's requested config is byte-identical to the org's list.
- It also holds for repo-level `allowed_actions: all` (still 409); only `local_only` is accepted, and only omitting a repo-level actions block entirely (which inherits the org's selected list automatically, verified) avoids the conflict.

This is a real module gap: a config that sets org-level `selected` and *also* restricts Actions on a specific repo is representable in YAML but guaranteed to fail at apply for every consumer, not just the fixture. Nothing in `validate-config.py` catches it before `terraform apply` finds out the hard way.

### `e2e-api` team is nested and set to `secret`

`tests/e2e/config/team/test-teams.yml` nests `e2e-api` under `e2e-backend` (itself under `e2e-platform`) and sets `privacy: secret`. GitHub requires nested teams to be `closed` — confirmed in the REST API docs and by the 422 above. Pure fixture bug, no module change needed; `validate_teams()` already accepts `secret` as a value because it's valid for non-nested teams, but doesn't yet check nesting.

## What Changes

- Add `validate_actions_tier_conflict()` to `scripts/validate-config.py`: when `config.yml` sets org-level `allowed_actions: selected`, flag every repository whose resolved (group + repo) actions config is non-empty, since GitHub will reject it at apply regardless of content. Reported as an error, not a warning — this is a guaranteed apply-time failure, the same severity class as the `required_checks` null-`for_each` bug, not a silent skip like the branch-protection tier warning.
- Fix the fixture: `tests/e2e/config.yml` org-level `actions` moves from `allowed_actions: selected` to `allowed_actions: all`, since the fixture's higher-value coverage is the repo-level restriction path (`restricted-actions-e2e` group, `e2e-actions-restricted` repo) — those need the org to stay permissive to be reachable at all.
- Fix the fixture: `e2e-api` team `privacy: secret` → `closed`.
- Add regression tests for the new validator.

No module resource code changes — `main.tf` and `modules/repository/main.tf` already do the right thing once handed a config; this is a documentation/pre-flight-validation gap, not a resource bug.

## Impact

- Affected specs: `repository-management` (new requirement documenting the org/repo actions conflict)
- Affected code: `scripts/validate-config.py`
- Affected fixture: `tests/e2e/config/config.yml`, `tests/e2e/config/team/test-teams.yml`
- Verified end-to-end: after both fixes, `terraform apply` against `gjed-io` succeeds (45 resources), `tests/verify_e2e.py` reports 33/33 checks passed, and `terraform destroy` cleans up completely.
- No breaking change: the new validator only fires for configs that were already guaranteed to fail at apply.
