## Context

The module ships with unit tests for validation logic (`tests/test_validate_*.py`) but has
no integration test. The only way to know the module actually works today is to run it by
hand against a real org. This is slow, error-prone, and never happens systematically.

The e2e fixture is a second, standalone Terraform root module that lives at `tests/e2e/`.
It references the module root via a local path (`source = "../../"`), so it always tests
the current source — not a published version. Running `terraform apply` in that directory
provisions real GitHub resources in a throwaway org; `verify.py` then asserts the API state
matches the declared config.

## Goals / Non-Goals

**Goals:**
- Cover every documented feature at least once in YAML config
- Be runnable by any developer against their own test org with `make e2e-apply`
- Produce actionable output on failure (which feature broke, expected vs actual)
- Work on `subscription: free` by default; document how to upgrade to `team`
- Leave no orphan resources (full `terraform destroy` cleans up completely)

**Non-Goals:**
- Running in CI automatically (no GitHub Actions workflow — that needs a dedicated test org
  and secrets management; a follow-on change can add it)
- Testing every permutation (one clear example per feature is enough)
- Replacing `terraform plan` as the primary day-to-day check

## Decisions

### Decision 1: Local source reference, not registry

`source = "../../"` instead of `source = "gjed/config-as-yaml/github"`.

**Why:** A published version would test the last release, not the current code. The fixture
must catch regressions introduced in the branch being developed.

**Alternative considered:** `source = "github.com/gjed/terraform-github-config-as-yaml"`
— rejected because it requires a published commit and doesn't reflect uncommitted changes.

### Decision 2: `subscription: free` as the default fixture config

The free tier is the lowest common denominator. It also lets us exercise the subscription-
gating logic: a private repo with a ruleset produces `subscription_warnings`; an org-scoped
ruleset produces `skipped_org_rulesets`. Both outputs are asserted by `verify.py`.

**Why not `team`:** Most contributors won't have a Team org lying around. Team-tier paths
are documented with upgrade instructions, not hard-wired.

### Decision 3: `e2e-` prefix for all resource names

All repositories, teams, webhooks, groups, rulesets, and branch protections defined in
the fixture use the `e2e-` prefix. This makes it trivial to distinguish test resources from
any real org content and makes `terraform destroy` safe (only the prefixed resources are
in state).

### Decision 4: PyGithub for post-apply verification, not a Terraform data source

`verify.py` calls the GitHub REST API directly after apply, instead of re-running Terraform
with data sources. 

**Why:** Data sources re-use provider auth and Terraform's plan engine — they test the
provider, not our config. A direct API call independently verifies that the provisioned
state on GitHub matches what the YAML declared, which is what matters.

**Alternative considered:** `terraform output` assertions only — rejected because outputs
don't cover resource properties (ruleset rules, team membership, branch protection settings)
that aren't surfaced in outputs.

### Decision 5: `membership_management_enabled = false` by default

Membership management is the highest-risk feature (removing a user from YAML ejects them
from the org). The fixture disables it by default and requires an explicit tfvars override
to test it.

### Decision 6: Partition feature tested via `repository_partitions = ["partitioned"]`

The fixture sets `repository_partitions = ["partitioned"]` and puts `e2e-partitioned-repo`
in `config/repository/partitioned/`. This exercises partition loading *and* proves that
top-level files are still loaded alongside partition files.

## Risks / Trade-offs

- **Requires a live GitHub org** → Mitigation: README documents creating a free throwaway
  org; `terraform validate` works without credentials for syntax checks.
- **webhook.site URLs expire/change** → Mitigation: URLs are documented placeholders; the
  README tells users to replace them. Webhook delivery failure doesn't break `terraform apply`.
- **Test org accumulates leftover resources if destroy is skipped** → Mitigation: `make
  e2e-destroy` is documented as the mandatory final step; the `e2e-` prefix makes manual
  cleanup trivial.
- **Real GitHub usernames required for team members** → Mitigation: team `members` and
  `maintainers` default to `[]`; adding real users is opt-in and documented.
- **PyGithub not in current requirements.txt** → Mitigation: only needed for `verify.py`;
  install instruction is in the README and Makefile help text. Not added to the root
  `requirements.txt` (test-only dependency).

## Migration Plan

1. Commit all new files on `feat/e2e-test-fixture`
2. No changes to existing source files; no migration needed
3. Merge when spec compliance and code quality reviews pass
4. CI integration (dedicated test org + GitHub Actions) is a follow-on change

## Open Questions

- Should `verify.py` check ruleset rules via the GitHub Rulesets API, or just check that
  the ruleset exists by name? (Current design: existence check only — rule-level assertion
  requires iterating ruleset details and is higher effort; leave as a future improvement.)
