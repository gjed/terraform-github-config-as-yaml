## Why

`repository_partitions` (shipped in `api-rate-limit-mitigation` for #36) cannot be safely used for its
intended purpose in a single Terraform state. Narrowing it from `[]` to a subset does not scope
Terraform to those repos — it removes every other repo's `for_each` key from `local.repositories`,
so Terraform plans to **destroy** every out-of-partition repository (#71). For a consumer with
~228 repos, narrowing to one partition plans destruction of 100+ repositories.

This is not fixable inside a single state: a `for_each` instance is either present in desired
config (refreshed) or absent (destroyed) — Terraform has no third "in state, not in config, leave
alone" bucket. `removed` blocks can't express it either (their `from` address can't carry instance
keys, so you can only forget the entire `module.repositories`, not one partition's worth). The
pending deletion-protection change (#37) does not rescue this and makes it strictly worse:
`prevent_destroy = true` fires on orphaned `for_each` instance keys whenever the resource **block**
still exists in config — which is exactly what partition narrowing does — so a narrowed plan would
permanently error on every out-of-partition repo instead of destroying it. It also makes the
proposed `archive_on_destroy` safety net dead code, since no destroy can ever reach `apply` while
the block exists.

`docs/scaling.md` currently ships the exact footgun it warns about two sections earlier: a GitHub
Actions example that computes `repository_partitions` from a git diff via `detect-partitions.sh`
and feeds the result into a `terraform plan` against a single shared state.

## What Changes

- Redefine `repository_partitions` as a **static state-sharding input**: one constant value per
  dedicated root module / backend, set once, never varied between plans against the same state.
  Dynamic narrowing against a shared state is documented as unsupported and dangerous — this is a
  docs/description change, not a removal; the variable, its type, and its default (`[]` = load
  everything) are unchanged, so existing consumers on a single state (the common case) see no
  behavior change.
- Add a `check "partition_narrowing"` block in `yaml-config.tf` that emits a **warning** (never
  fails the plan) whenever `repository_partitions` selects a strict, non-empty subset of the
  discovered partitions, pointing at the state-sharding requirement. This is the only in-module
  guard available — Terraform config cannot inspect its own state, so a hard failure or a precise
  "this will destroy N repos" check is not implementable.
- Retarget `scripts/detect-partitions.sh` and `docs/scaling.md`'s CI example: partition detection
  now selects which **per-partition root module / CI job** to run (each with its own backend), not
  a `TF_VAR` fed into one shared-state plan. The script's logic and `--tfvar` output are unchanged;
  only its documented purpose and the Actions example change.
- Document `-refresh=false` on PR/merge plans plus a scheduled full-refresh plan as the primary,
  headline way to cut plan API cost for large orgs on a single state — it needs zero state
  migration and carries zero destroy risk, unlike partitioning.
- Amend the pending `protect-repos-from-deletion` change (#37, not yet implemented) in place: drop
  `prevent_destroy = true` from the plan entirely — it deadlocks against partition narrowing and,
  independent of partitioning, turns the module's normal decommission path (delete the YAML entry)
  into a guaranteed plan error requiring manual `state rm` surgery. Keep `archive_on_destroy` as
  the sole safety net, defaulting to `false` for this release to preserve current destroy behavior;
  flipping the default to `true` is deferred to the next major version and tracked as a follow-up.

## Capabilities

### Modified Capabilities

- `repository-partitioning`: partition selection is now specified as a static state-sharding
  mechanism only; add a requirement for the narrowing warning check.
- `partition-detection`: retarget the script's purpose to CI job/root-module selection instead of
  feeding a shared-state `terraform plan`.
- `scaling-documentation`: require the `-refresh=false` pattern as the primary scaling guidance;
  replace the single-state partition CI example with a multi-root-module example; require the
  destroy-risk warning to say what is actually safe instead of pointing at #37.
- `deletion-protection` (pending, unimplemented change `protect-repos-from-deletion`): drop the
  `prevent_destroy = true` requirement and its scenarios; `archive_on_destroy` becomes the sole
  protection mechanism, defaulting to `false` for now.

## Impact

- `variables.tf` — rewrite `repository_partitions` description
- `yaml-config.tf` — add `check "partition_narrowing"`
- `docs/scaling.md` — new `-refresh=false` section as primary guidance; rewrite the Partitioning
  section around per-partition root modules/backends; delete the single-state Actions example;
  fix the warning box that currently points at #37 for protection
- `scripts/detect-partitions.sh` — header/help text retargeted to job/root-module selection (logic
  unchanged)
- `examples/consumer/main.tf` — update partition comments to the sharding contract
- `openspec/changes/protect-repos-from-deletion/` — proposal, design, and
  `specs/deletion-protection/spec.md` amended in place (still unimplemented, no archive/migration
  needed)
- No breaking change: `repository_partitions` keeps its type, default, and loading behavior;
  the new `check` block only warns.
