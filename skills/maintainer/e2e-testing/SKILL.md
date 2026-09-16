---
name: e2e-testing
description: >-
  Run the end-to-end test fixture for the terraform-github-config-as-yaml repository against a
  real GitHub test organization. MAINTAINER-ONLY — do not use when consuming the published
  module. Use when running e2e tests, verifying module changes against live GitHub, or cleaning
  up the e2e fixture. Triggers on "run e2e", "e2e tests", "test fixture", or make e2e-* targets.
---

# E2E testing (maintainer only)

The fixture in `tests/e2e/` applies the module against a dedicated GitHub test organization and
verifies live results. It creates and destroys real repositories — never point it at a
production organization.

## Prerequisites

- `GITHUB_TOKEN` with admin rights on the **test** organization.
- `tests/e2e/terraform.tfvars` (copy from `tests/e2e/terraform.tfvars.example`).

## Lifecycle

Run from the repo root, in order:

```bash
make e2e-init        # terraform init in tests/e2e
make e2e-validate    # terraform validate
make e2e-plan        # preview fixture changes
make e2e-apply       # create fixture resources on the test org
make e2e-verify      # assert live GitHub state matches expectations (tests/verify_e2e.py)
make e2e-destroy     # ALWAYS tear down when done
```

Each target delegates to `tests/e2e/Makefile`.

## Discipline

- **Teardown is mandatory.** Leftover fixture repos pollute the test org and break the next run.
  If a run aborts midway, run `make e2e-destroy` before anything else.
- Verify failures: read `tests/verify_e2e.py` output first — it reports the exact live-vs-expected
  mismatch. Only then inspect Terraform state or the test org.
- Fixture config lives under `tests/e2e/config/`; it mirrors the consumer contract. Keep it
  minimal — it is a test surface, not documentation.
- Rate limits: the fixture counts against the test org's API quota (~5000 req/h). Avoid rapid
  apply/destroy loops.
