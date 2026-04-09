## Context

The module currently loads all `*.yml` files from `config/repository/` via a flat `fileset()` call. Every `terraform plan` refreshes every repository and its associated resources (teams, collaborators, rulesets, actions permissions, webhooks), consuming ~7 GitHub API calls per repository. At 700+ repos with PAT authentication (5,000 requests/hour limit), a single plan can exhaust the rate limit. Even with GitHub App tokens (15,000/hour), the ceiling is around 2,000 repos.

There is no mechanism to scope a plan to a subset of repositories. Users must resort to `-target` flags or state splitting, both of which are manual and error-prone.

## Goals / Non-Goals

**Goals:**

- Allow users to organize repository config files into subdirectories (partitions) under `config/repository/`
- Allow users to select which partitions to load via a module variable, reducing the number of repos in a single plan
- Provide a CI helper script that maps git changes to affected partitions
- Document scaling considerations, API cost breakdown, and partitioning strategy

**Non-Goals:**

- Per-repository filtering (partitions operate on directory granularity, not individual repos)
- Automatic rate limit detection or retry logic (the provider handles retries; this change reduces the request volume)
- Terraform state splitting or multiple module instances (this is a consumer-side decision, not a module concern)
- Resource-level toggles like `manage_webhooks = false` (current empty-map-skips-resource behavior is sufficient)
- Repository deletion protection (tracked separately in #37)

## Decisions

### 1. Subdirectory-based partitioning over glob/name filters

**Decision:** Partitions are subdirectories under `config/repository/`. A `repository_partitions` variable selects which subdirectories to load.

**Alternatives considered:**
- Glob patterns on repo names (e.g., `repository_filter = ["infra-*"]`): Requires loading all YAML first, then filtering. Doesn't reduce file I/O at plan time. Also fragile — repo renaming breaks filters.
- Group-based filtering: Overloads the existing group concept which is about configuration inheritance, not operational partitioning.

**Rationale:** Subdirectories map directly to filesystem paths, making git diff detection trivial. The partitioning concern (which repos to plan) is orthogonal to the grouping concern (what settings repos share). Keeping them separate avoids coupling.

### 2. Top-level files always loaded

**Decision:** `*.yml` files directly in `config/repository/` (not in subdirectories) are always loaded regardless of `repository_partitions` value.

**Rationale:** Top-level files serve as the "common" or "always-on" partition. Repos that don't belong to any partition, or that should always be included in every plan, live here. This also ensures backward compatibility — existing flat layouts work without changes.

### 3. Empty list means all partitions

**Decision:** `repository_partitions = []` (default) loads all subdirectories. Only a non-empty list restricts loading.

**Rationale:** Opt-in filtering. Users who don't need partitioning get identical behavior to today. No migration required.

### 4. Single level of nesting

**Decision:** Only one level of subdirectories is supported. `config/repository/infra/sub/file.yml` is not loaded.

**Rationale:** Keeps `fileset()` patterns simple and the mental model flat. Nested partitioning adds complexity without clear benefit — if you need finer granularity, create more top-level partitions.

### 5. Validation via Terraform check block

**Decision:** A `check` block validates that all requested partition names correspond to existing subdirectories.

**Rationale:** Catches typos and misconfiguration at plan time rather than silently loading no repos. Uses Terraform's native `check` mechanism (warning, not hard error) consistent with existing template validation.

### 6. Partition detection script uses git diff

**Decision:** A bash script analyzes `git diff` output to determine affected partitions. Shared config changes (`config/group/`, `config/ruleset/`, `config/webhook/`, `config/config.yml`) trigger all partitions. Changes to `config/repository/<partition>/` trigger only those partitions. Changes to only top-level `config/repository/*.yml` trigger no partitions (those files are always loaded anyway).

**Rationale:** Git is the source of truth for what changed. The script bridges git's file-level change tracking with Terraform's partition variable, enabling CI pipelines to run targeted plans.

## Risks / Trade-offs

- **[Partition switching causes destroy plans]** → When `repository_partitions` changes from `[]` to `["infra"]`, repos in other partitions disappear from Terraform's view and show as planned destroys. **Mitigation:** Document this clearly. Repository deletion protection (#37) provides the safety net. The script helps CI avoid accidental partition narrowing.

- **[Duplicate repo names across partitions]** → A repo defined in both `infra/repos.yml` and `platform/repos.yml` causes a Terraform error (duplicate key in merge). **Mitigation:** Existing duplicate detection logic already catches this — it maps keys to filenames and errors on duplicates. The filenames now include partition prefixes (e.g., `infra/repos.yml`), so the error message remains helpful.

- **[Shared config changes require full plan]** → Changing a group, ruleset, or webhook definition triggers all partitions because those changes can affect any repository. **Mitigation:** This is correct behavior — you genuinely need to plan all repos when shared config changes. The detection script handles this automatically.

- **[Script maintenance burden]** → The detection script encodes knowledge about the config directory structure. If the structure changes, the script needs updating. **Mitigation:** The script is simple (< 50 lines of bash) and the directory structure is stable. Document the assumptions.
