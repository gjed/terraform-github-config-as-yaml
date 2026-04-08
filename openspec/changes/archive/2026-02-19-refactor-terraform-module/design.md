# Design: Reusable Terraform Module

## Context

The current repo is a monolith: Terraform logic, provider configuration, and user config files all live
together. Anyone wanting to adopt it for a new org must fork the entire repo and keep Terraform
internals in sync manually. The goal is to separate the infrastructure layer (the module) from the
consumer layer (config files + minimal entrypoint).

Stakeholders: maintainers of this repo, any org adopting the YAML-driven config pattern.

## Goals / Non-Goals

- **Goals:**
  - Publish the Terraform logic as a callable module (via git ref or Terraform Registry).
  - Consumers only maintain YAML config files and a ~15-line `main.tf`.
  - The module remains self-contained: all YAML parsing logic stays inside the module.
  - Scripts and pre-commit tooling work correctly with the module-wrapped state paths.
  - Provide a minimal consumer example/template.
- **Non-Goals:**
  - Publishing to the Terraform Registry (initial release is git-ref based; registry publication is a
    follow-up).
  - Changing the YAML config schema or merging logic.
  - Converting this repo itself into a consumer (this repo stays as the source-of-truth module).

## Decisions

### Decision: `config_path` as a module variable

**What:** Replace the hardcoded `"${path.module}/../config"` base path with `var.config_path`.
Consumers pass `"${path.root}/config"`.

**Why:** Terraform's `file()` and `fileset()` require paths known at plan time. A variable works as
long as consumers provide a static string (e.g. `"${path.root}/config"`). A computed value would
break plan-time evaluation — this limitation must be documented clearly.

**Alternatives considered:**

- Pre-processing YAML outside Terraform and passing structured data in: rejected — it pushes
  complexity onto consumers and breaks the self-contained nature of the module.
- Embedding config inside the module: rejected — consumers cannot customise their config without
  forking the module.

### Decision: Provider removed from module root

**What:** The `provider "github"` block is removed. Consumers configure their own provider.

**Why:** Terraform modules must not configure providers (it is a Terraform anti-pattern and will
produce warnings/errors in newer provider versions). The `owner` was previously read from the YAML
`organization` field, but provider configuration happens before module evaluation, so the YAML value
is unavailable at provider-configuration time.

**Consequence:** Consumers set `owner` in their own provider block. The `organization` output still
exposes the org name derived from YAML for reference, but it no longer drives provider configuration.

### Decision: Scripts updated for nested module state paths

**What:** `onboard-repos.sh` and `offboard-repos.sh` will accept or auto-detect an
`--module-path` flag that prepends `module.github_org.` to the state resource address used in
`terraform import` / `terraform state rm` commands.

**Why:** When consumers wrap the module, the Terraform state path for a repository becomes
`module.github_org.module.repositories["repo-name"]` rather than `module.repositories["repo-name"]`.
The scripts need to handle both the template-repo (direct) and consumer (wrapped) layouts.

### Decision: Consumer template as a directory in this repo

**What:** Add an `examples/consumer/` directory containing a minimal consumer setup with placeholder
`main.tf`, empty `config/` stubs, and a `README.md`.

**Why:** Keeps the example co-located and version-controlled with the module. A separate template repo
is a future option but adds maintenance overhead now.

## Risks / Trade-offs

- **State migration for existing forks:** Any fork currently using this repo as a root module will
  see state path changes when wrapping in `module "github_org"`. Mitigation: document the migration
  path (state mv commands) in the consumer README; provide a migration script stub.
- **`config_path` static constraint:** If a consumer tries to use a computed value for `config_path`
  (e.g. from a data source), Terraform will fail at plan time. Mitigation: document this constraint
  prominently and validate in CI.
- **Script complexity:** Supporting both direct and wrapped module paths in the scripts increases
  their complexity. Mitigation: make `--module-path` explicit and optional; default to empty
  (direct layout).

## Migration Plan

For existing forks that currently use this repo as a root module:

1. Wrap existing Terraform in a `module "github_org"` block pointing to the new versioned source.
1. Run `terraform state mv` for each repo resource from `module.repositories["x"]` to
   `module.github_org.module.repositories["x"]`.
1. Add a provider block with `owner = "<org>"` to the consumer `main.tf`.
1. Remove the local fork's `terraform/` directory.

A migration helper script (`scripts/migrate-state.sh`) will be provided as part of this change.

## Open Questions

- Should we target the Terraform Registry as part of this change, or defer it? (Issue says git-ref
  based initially — deferring Registry publication.)
- Should the module expose an `organization` output so consumers can reference it without reading
  the YAML themselves? (Yes — `organization` is already in `outputs.tf`; just ensure it is exposed
  from the module.)
