## Context

This module manages GitHub organization configuration as YAML. It already handles repositories,
groups, rulesets, webhooks, teams, membership, branch protections, Actions permissions, and
organization settings. Secrets and variables (for both Actions and Dependabot) are the last major
gap in the configuration surface.

The existing pattern for sensitive values is well-established: webhook secrets use `env:VAR_NAME`
references in YAML, resolved at plan time via the `webhook_secrets` Terraform variable. This
design extends that same pattern to Actions/Dependabot secrets.

The module follows a consistent architecture: YAML files in `config/` directories are loaded in
`yaml-config.tf`, merged per-repository with group inheritance, and passed to `modules/repository/`
for resource creation. Organization-level resources are created directly in root-level `.tf` files.

## Goals / Non-Goals

**Goals:**

- Manage org-level and repo-level Actions secrets, Actions variables, and Dependabot secrets via YAML
- Reuse the existing `env:VAR_NAME` pattern for secret value resolution
- Support group inheritance with repo-level overrides (consistent with webhooks, teams, etc.)
- Support org-level secret visibility scoping: `all`, `private`, `selected` (with repo name list)
- Validate configuration at plan time (undefined references, missing values)
- Work on all subscription tiers (no tier-gating for secrets/variables)

**Non-Goals:**

- Vault/AWS Secrets Manager/Azure Key Vault integration (future enhancement; start with `env:` only)
- Dependabot variables (GitHub does not support org-level Dependabot variables)
- Actions environment secrets/variables (environment management is a separate concern)
- CodeQL / code scanning secret management
- Automatic secret rotation

## Decisions

### 1. Config directory structure: `config/secret/` for org-level definitions

**Decision:** Create a new `config/secret/` directory for org-level secret and variable definitions,
separate from `config/config.yml`.

**Alternatives considered:**

- *Inline in config.yml:* Would bloat config.yml and mix concerns. config.yml is for org settings
  and global defaults, not secret inventories.
- *Separate directories per type (`config/actions-secret/`, `config/dependabot-secret/`):* Over-fragmented
  for what is logically a single concern. Webhooks use a single `config/webhook/` directory for
  the same reason.

**Rationale:** Mirrors the `config/webhook/` pattern. Multiple YAML files in the directory are
merged (alphabetical order, last-wins for duplicate keys). This keeps org-level definitions
out of config.yml while allowing users to organize by team, environment, or purpose.

### 2. YAML schema for org-level secrets

**Decision:** Use a flat key-per-secret structure with explicit `type` discriminator:

```yaml
# config/secret/org-secrets.yml
DEPLOY_TOKEN:
  type: actions_secret
  value: "env:DEPLOY_TOKEN"
  visibility: selected
  selected_repositories:
    - my-app
    - my-api

ENVIRONMENT:
  type: actions_variable
  value: "production"
  visibility: all

REGISTRY_PASSWORD:
  type: dependabot_secret
  value: "env:REGISTRY_PASSWORD"
  visibility: private
```

**Alternatives considered:**

- *Nested structure (`actions_secrets: { ... }`, `actions_variables: { ... }`, `dependabot_secrets: { ... }`):*
  Proposed in the issue. More intuitive grouping but creates three separate merge paths. With a `type`
  field, all entries share one loading/merging pipeline.
- *Same flat structure but without `type` (infer from `value` pattern):* Ambiguous — a variable
  could also use `env:` for dynamic values.

**Rationale:** The `type` discriminator is explicit, avoids ambiguity, and simplifies the Terraform
locals (one `for` loop with a type filter, rather than three separate file-loading blocks). The
trade-off is slightly more verbose YAML, but clarity wins for a security-sensitive feature.

**Update after reconsideration:** The issue's nested structure (`actions_secrets:`, `actions_variables:`,
`dependabot_secrets:`) is actually more ergonomic and matches what users expect from GitHub's own
UI grouping. The `type` discriminator approach saves code but hurts readability. Going with the
**nested structure from the issue** — three top-level keys per file, each containing a map of
name → config. This costs slightly more Terraform locals code but produces more intuitive YAML.

Final schema:

```yaml
# config/secret/org-secrets.yml
actions_secrets:
  DEPLOY_TOKEN:
    value: "env:DEPLOY_TOKEN"
    visibility: selected
    selected_repositories:
      - my-app
      - my-api

actions_variables:
  ENVIRONMENT:
    value: "production"
    visibility: all

dependabot_secrets:
  REGISTRY_PASSWORD:
    value: "env:REGISTRY_PASSWORD"
    visibility: private
```

### 3. YAML schema for repo-level secrets/variables

**Decision:** Add `secrets` and `variables` keys to group and repository configs:

```yaml
# In group or repository config
secrets:
  actions:
    DATABASE_URL:
      value: "env:MY_REPO_DATABASE_URL"
  dependabot:
    REGISTRY_PASSWORD:
      value: "env:REGISTRY_PASSWORD"
variables:
  actions:
    DEPLOY_ENV:
      value: "staging"
```

**Rationale:** Matches the issue's proposed schema. Nesting under `secrets.actions` and
`secrets.dependabot` avoids name collisions (an Actions secret and a Dependabot secret
can share the same name on GitHub). Variables only support `actions` (GitHub has no
Dependabot variables at the org or repo level).

### 4. Secret value resolution: reuse `webhook_secrets` pattern with new variable

**Decision:** Add a new `secret_values` input variable (sensitive `map(string)`) that works
identically to `webhook_secrets`. YAML values using `env:VAR_NAME` are resolved against this
map at plan time.

**Alternatives considered:**

- *Extend `webhook_secrets` to cover all secrets:* Mixing concerns — webhook secrets and
  Actions secrets serve different purposes and may be managed by different teams.
- *One variable per secret type:* Over-granular. A single `secret_values` map is simpler
  and mirrors how most CI/CD systems inject secrets (flat namespace).

**Rationale:** Clean separation from webhook secrets. Users pass one additional variable with
all their secret values. The `env:` prefix in YAML makes it obvious which values are sensitive.

### 5. Group inheritance: merge strategy

**Decision:** Secrets and variables follow the same merge strategy as webhooks:

- Groups are applied in order; later groups override by key (secret/variable name)
- Repo-level definitions override group-level by key
- No merging of individual secret properties — if a repo overrides a secret, it replaces
  the entire definition

**Rationale:** Consistent with existing module behavior. Partial merges of secret properties
would be confusing (e.g., overriding just `visibility` but inheriting `value`).

### 6. `selected_repositories` resolution

**Decision:** Org-level secrets with `visibility: selected` reference repository names in
`selected_repositories`. These are resolved to repository IDs using a data source lookup
against the repos managed by this module (from `local.repos_yaml`).

**Rationale:** Users already reference repos by name everywhere else. Name-to-ID resolution
is an internal concern. Only repos managed by this module can be referenced — external repo
names would require a data source lookup that could fail and is out of scope.

### 7. Implementation location

**Decision:**

- **Org-level resources:** New `org-secrets.tf` file at root level (mirrors `org-webhooks.tf`,
  `org-rulesets.tf` pattern)
- **Repo-level resources:** Inside `modules/repository/` (mirrors existing repo-level resource pattern)
- **YAML loading/merging:** In `yaml-config.tf` (extends existing locals)

**Rationale:** Follows established file organization. Org resources at root, repo resources
in the repository module, config parsing centralized in yaml-config.tf.

## Risks / Trade-offs

- **[Risk] Secrets in Terraform state** → Mitigation: Document the need for encrypted remote
  backends (S3 with encryption, Terraform Cloud, etc.). This is inherent to Terraform's secret
  management model, not specific to this feature.

- **[Risk] API rate limits with many secrets** → Mitigation: Each secret is one API call.
  Organizations with hundreds of secrets may approach rate limits during initial apply. Document
  this and suggest batching with `-parallelism` flag.

- **[Risk] `selected_repositories` references stale repo names** → Mitigation: Terraform
  validation checks at plan time ensure referenced repos exist in the configuration. If a
  repo is removed from config but still referenced in a secret's `selected_repositories`,
  the plan will surface the error.

- **[Trade-off] Single `secret_values` variable vs. per-type variables** → Simpler interface
  but loses the ability to scope access by secret type. Acceptable for the common case; users
  with advanced needs can wrap the module.

- **[Trade-off] No Vault/KMS integration** → Starting with `env:` only keeps scope manageable.
  The `value` field pattern is extensible — future prefixes like `vault:` or `aws-sm:` can be
  added without breaking existing configs.

## Open Questions

- Should `Dependabot variables` be added at the repo level if/when GitHub adds API support?
  (Currently not supported by the GitHub provider.)
- Should there be a way to mark a secret as "imported" (managed externally, read-only in
  Terraform) to avoid conflicts with secrets set via GitHub UI or other tooling?
