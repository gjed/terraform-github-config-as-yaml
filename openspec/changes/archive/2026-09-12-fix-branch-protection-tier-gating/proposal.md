## Why

`local.merged_branch_protections` applies branch protections to every repository regardless of
subscription tier or visibility. The comment at `yaml-config.tf:799` states:

> No subscription tier filtering - branch protection works on all tiers including free-tier
> private repos

This is factually wrong. GitHub's documentation states:

> Protected branches are available in public repositories with GitHub Free and GitHub Free for
> organizations. Protected branches are also available in public **and private** repositories with
> GitHub Pro, GitHub Team, GitHub Enterprise Cloud, and GitHub Enterprise Server.

Free-tier organizations cannot use branch protection on private repositories. The module attempts
it anyway, so `terraform apply` fails with an API rejection instead of skipping the unsupported
feature.

Repository rulesets already handle this correctly via `local.rulesets_require_paid_for_private`,
which filters private repos on `free` and surfaces them in `subscription_warnings`. Branch
protections have no equivalent gate.

This is not theoretical. The e2e fixture (`tests/e2e/`) configures `subscription: free` and
attaches `branch_protections: [e2e-main-bp]` to the `internal-e2e` group, which two **private**
repositories inherit. The fixture cannot complete an apply against a free-tier org until this
is fixed.

## What Changes

- Add `local.branch_protections_require_paid_for_private`, mirroring the existing
  `rulesets_require_paid_for_private` gate.
- Add `local.effective_branch_protections`, which returns an empty map for private repositories
  on the `free` tier and is consumed in place of `merged_branch_protections`.
- Add `local.repos_with_skipped_branch_protections` to track affected repositories.
- Add a `skipped_branch_protections` output, mirroring the shape of `skipped_org_rulesets`.
- Emit a warning from `scripts/validate-config.py` when branch protections are configured for
  private repositories on `free`, so the problem surfaces before `terraform plan`.

The public YAML interface does not change. Configuration that is valid today stays valid; the
only behavioural change is that an unsupported combination is now skipped and reported rather
than attempted and failed.

## Impact

- Affected specs: `repository-management` (Subscription Tier Awareness)
- Affected code: `yaml-config.tf`, `outputs.tf`, `scripts/validate-config.py`
- Consumers on `free` with branch protections on private repos: those protections were never
  actually applied — the apply failed. After this change the apply succeeds and the skipped
  repositories are listed in `skipped_branch_protections`.
- Consumers on `pro`, `team`, or `enterprise`: no change.
- The new output is additive. `subscription_warnings` keeps its current ruleset-only meaning
  and shape, so existing consumers reading it are unaffected.
