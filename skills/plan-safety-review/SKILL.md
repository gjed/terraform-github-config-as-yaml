---
name: plan-safety-review
description: >-
  Review a Terraform plan for destructive or high-risk changes before apply. Use after any
  `make plan` / `terraform plan` in a config-as-yaml repo, or when the user asks "is this plan
  safe", "review the plan", or before every `terraform apply` that touches production GitHub
  state.
---

# Plan safety review

Never let an apply proceed on an unreviewed plan. Work from the machine-readable plan, not
the human rendering.

## Workflow

1. Produce a plan file: `make plan` (saves `tfplan`) or `terraform plan -out=tfplan`.
2. Extract resource changes:

   ```bash
   terraform show -json tfplan > /tmp/plan.json
   jq -r '.resource_changes[] | select(.change.actions != ["no-op"]) |
     "\(.change.actions | join(","))\t\(.address)"' /tmp/plan.json
   ```

3. Classify and report every non-no-op change, most dangerous first.

## Red flags — require explicit human confirmation

- **Any `delete`, or a replace (`delete,create` / `create,delete`)** on `github_repository` —
  repository destruction or recreation. Recreation loses issues, PRs, stars, and watchers.
- **Visibility flips**, especially `private` → `public`: check
  `.change.before.visibility != .change.after.visibility` on `github_repository`.
- **`github_membership` deletions** — removes a person from the organization, revoking all
  private-repo access and destroying their private forks.
- **`github_team` / `github_team_repository` deletions** — access removal for whole teams.
- **Ruleset or branch-protection deletions** — silently drops enforcement (force-push,
  deletion, review requirements) on live branches.
- **Large blast radius**: a one-repo change should touch a handful of resources. Dozens of
  changed resources from a small diff usually means a group/ruleset edit fanned out —
  verify that fan-out is intended.

## Yellow flags — mention, no block

- Archive toggles, topic/description churn, webhook secret rotations (always show as
  changes because secrets are write-only), `github_actions_*` permission tightening.

## Output format

Summarize as: counts per action (`create` / `update` / `replace` / `delete`), then a list of
red-flag items with resource address and before → after for the risky attribute. End with an
explicit safe / needs-confirmation verdict.
