## Context

`yaml-config.tf:26-43` filters `local.repositories` down to the top-level files plus files from
`setintersection(active_partitions, repository_partition_dirs)`. `main.tf:27` then does
`for_each = local.repositories`. When `repository_partitions` narrows from `[]` to a subset, repos
outside that subset vanish from the `for_each` key set while remaining in state — standard
Terraform semantics plan that as a destroy. `modules/repository/main.tf:38` currently has
`prevent_destroy = false`, so nothing blocks it. The only existing guard,
`check "valid_partitions"` (`yaml-config.tf:1148`), validates that requested partition **names**
exist as subdirectories; it says nothing about narrowing being destructive.

The pending, unimplemented `protect-repos-from-deletion` change (#37) proposed
`prevent_destroy = true` as a primary guard. It does not help here and actively conflicts:
`prevent_destroy` is evaluated per resource instance against the resource's config **block**. A
narrowed partition removes the module's `for_each` **key**, not the block — the block stays in
config — so every orphaned instance still resolves to a `prevent_destroy = true` block and plan
**errors** instead of destroying. That is a permanent, unfixable CI failure on any partition-scoped
plan, not a safety net. It also makes the proposed `archive_on_destroy` argument unreachable: no
destroy can reach `apply` while the block is present and protected, and `terraform state rm`
bypasses the provider entirely, so archiving never fires either way.

## Goals / Non-Goals

**Goals:**

- Eliminate the destroy-on-narrow footgun for the common case (single shared state) by redefining
  how `repository_partitions` may be used, without removing the variable or breaking existing
  multi-state consumers.
- Give the module a genuinely safe primary answer to "reduce plan API cost" that works in a single
  state with zero destroy risk: `-refresh=false` PR plans + a scheduled full-refresh plan as drift
  authority.
- Fix the pending #37 proposal so it stops conflicting with partitioning and stops blocking normal
  repo decommissioning.

**Non-Goals:**

- Detecting narrowing-against-shared-state from inside Terraform with certainty. Terraform config
  cannot read its own state; a `check` block can only compare the requested partition list against
  discovered directories, so the best available guard is a warning, not a hard failure.
- Removing `repository_partitions` or `detect-partitions.sh`. Static per-partition-state sharding
  is a legitimate, real answer at 2,000+ repos where even a nightly full-refresh plan can exceed
  API limits; throwing it away abandons that tier.
- Implementing `archive_on_destroy` default flip to `true` in this change — deferred to the next
  major version per explicit decision (see Decisions).

## Decisions

### Decision 1: Redefine partitioning as static state-sharding, don't deprecate it

**Choice:** Keep `repository_partitions` with its current type/default. Change its documented
contract: each non-empty value must be paired with its own dedicated Terraform state (its own root
module + backend), set once at bootstrap and never varied between plans against that same state.
Dynamic, CI-computed narrowing against a shared state is explicitly unsupported.

**Alternatives considered:**

- *Deprecate/remove the variable entirely, document only `-refresh=false`.* Rejected: this quietly
  abandons the >2,000-repo tier the module's own scaling docs use to justify the feature in the
  first place. Even a nightly full-refresh plan exceeds a GitHub App token's 15k/hour limit past
  roughly that size; state sharding is the standard answer there, and the multi-state pattern needs
  zero new module code — consumers just instantiate the module N times in N root modules, each
  pinning a constant partition value.
- *Detect the trap and hard-fail (`assert` instead of `warning`) inside the module.* Rejected as
  infeasible: a `check`/`assert` can see variables and provider data, not state instance
  addresses. A `github_repositories` data source tells you what exists in the org, not what a given
  state manages, and burns exactly the API budget partitioning exists to save. There is no reliable
  in-module signal to distinguish "narrowing a dedicated per-partition state (safe)" from "narrowing
  a shared state (destroys everything else)".

**Rationale:** Preserves the only safe use of the variable (already representable today with zero
code changes — just N root modules) while being honest that the single-state dynamic-narrowing
pattern the docs currently ship is the actual defect.

### Decision 2: Warning-only `check` block for narrowing detection

**Choice:** Add `check "partition_narrowing"` that emits a warning (never fails the plan) whenever
`0 < length(var.repository_partitions) < length(local.repository_partition_dirs)`.

**Rationale:** This is the one signal available from inside the config: "you selected a strict
subset of the partitions that exist on disk." It cannot know whether the current state also
contains the other partitions' repos, but for the target audience (dynamic CI narrowing against a
shared state) that's exactly the case that trips it, every run, until they either load everything
or move to a dedicated per-partition state. Warning, not error, because legitimate dedicated
per-partition states also trip this condition on every single plan — an error there would be a
permanent false-positive block on a supported pattern.

### Decision 3: Retarget `detect-partitions.sh` and the docs, don't touch the script's core logic

**Choice:** The script's file-classification and escalation logic (shared config → all partitions,
partition file → that partition, top-level file → none) stays as-is; it is still exactly the right
logic for "which partitions did this diff touch." What changes is what the caller does with the
output: select which per-partition **root module / CI job** to run, never feed it as
`TF_VAR_repository_partitions` into a single shared-state plan. Update the script's header comment
and `--help` text to say so; the `--tfvar` JSON-array output stays because it's still useful for
driving a CI matrix of per-partition jobs.

**Rationale:** The bug was never in the detection logic — it correctly identifies which partitions a
diff touches. The bug is in what `docs/scaling.md`'s example does with that list.

### Decision 4: Drop `prevent_destroy = true` from #37; keep `archive_on_destroy` alone, default `false` for now

**Choice:** Amend `protect-repos-from-deletion` (still unimplemented — no migration needed) to
remove `prevent_destroy = true` and its requirement/scenarios entirely. Keep `archive_on_destroy`
as the sole mechanism, module variable, default `false` (current behavior preserved), plumbed from
`config/config.yml` `defaults:` exactly as originally designed. Flipping the default to `true` is a
deliberate behavior change (destroy now archives instead of deletes) and is deferred to the next
major version so it ships with a loud, isolated changelog entry rather than bundled into a bugfix.

**Alternatives considered:**

- *Gate `prevent_destroy` behind a variable defaulting to `false`.* Impossible: Terraform requires
  `prevent_destroy` to be a literal boolean; variables, locals, and conditional expressions are
  rejected at parse time. The original design.md already concedes this for the "configurable"
  alternative — it should not have been listed as a viable option for issue #71's resolution either.
- *Keep `prevent_destroy = true`, only fix partitioning.* Rejected: independent of partitioning,
  `prevent_destroy = true` breaks the module's own normal decommission path — deleting a repo's
  YAML entry is `for_each` key removal, which would now permanently error instead of applying,
  forcing every legitimate removal through manual `state rm` surgery. That's hostile UX unrelated
  to #71 and not worth the marginal protection over `archive_on_destroy` alone.
- *Ship `archive_on_destroy` default `true` now.* Considered and explicitly rejected per user
  direction: ship default `false` in this change to preserve current behavior; default flips to
  `true` in the next major version.

## Risks / Trade-offs

**[Warning fatigue on legitimate multi-state consumers]** Any consumer correctly using a dedicated
per-partition state will see the narrowing warning on every plan. **Mitigation:** the warning text
explains the supported pattern; `check` warnings don't fail CI, so this is noise, not breakage.

**[No hard stop for the actual footgun]** A consumer who ignores the warning and narrows against a
shared state is still one `terraform apply` away from mass destroy. **Mitigation:** this is the
best available signal from inside Terraform; the real fix is the rewritten docs/example no longer
demonstrating the dangerous pattern, since most consumers copy the shipped example verbatim.

**\[archive_on_destroy default stays `false`\]** Repos removed from YAML today are still deleted, not
archived, until the next major version. **Mitigation:** this preserves current behavior exactly —
no surprise for existing consumers — and the default-flip is tracked as explicit, isolated future
work rather than silently bundled into this fix.
