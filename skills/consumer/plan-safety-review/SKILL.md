---
name: plan-safety-review
description: >-
  Review a saved Terraform plan for destructive or risky changes before applying it against a
  GitHub organization. Use after `terraform plan -out=tfplan` (or `make plan`) and before any
  `terraform apply` — especially when the user asks "is this plan safe", "review the plan",
  "what will this destroy", or when a plan touches repository visibility, members, teams, or
  branch protections.
---

# Plan safety review

A Terraform apply against a GitHub organization can destroy repositories, expose private code,
or revoke people's access. Review every plan mechanically before applying.

## Get the plan as JSON

```bash
terraform show -json tfplan > tfplan.json
```

Inspect `resource_changes[]`: each entry has `address`, `type`, and `change.actions`.

## Blocking findings — require explicit human confirmation

Flag each occurrence with its address; never apply without the user acknowledging every one:

1. **Deletes** — any `change.actions` containing `"delete"` (including `["delete", "create"]`
   replacements). `github_repository` deletion destroys the repository and its issues/PRs/wiki.
2. **Visibility exposure** — `github_repository` where `change.before.visibility` is
   `private`/`internal` and `change.after.visibility` is `public`. This publishes the code.
3. **Member removals** — deletion of `github_membership` removes the person from the
   organization, revoking all private-repo access and destroying their private forks.
4. **Protection downgrades** — deletion of `github_repository_ruleset`,
   `github_organization_ruleset`, or branch-protection resources, or `enforcement` moving from
   `active` to `evaluate`/`disabled`.
5. **Permission escalation** — team or collaborator permission changes upward (e.g. `push` →
   `admin`), and `github_membership` role changing `member` → `admin`.

## Advisory findings — summarize but do not block

- Archived-repository edits (usually fail at apply time; suggest offboarding instead).
- Large blast radius: more than ~20 changed resources — recommend `make plan-repo REPO=<name>`
  targeting or applying in slices.
- Default-branch renames (breaks clones and open PRs).

## Report format

Output a short table: address, action, finding class, before → after for the risky attribute.
End with a verdict: `SAFE TO APPLY`, or `NEEDS CONFIRMATION: <n> blocking findings`.

## Out-of-band drift check (optional MCP)

When a plan shows unexpected changes, the cause is often out-of-band edits in the GitHub UI. If
a read-only GitHub MCP server (`github` in the repo's `.mcp.json`) is available, inspect the
live repository/org state and compare it with the YAML intent to confirm drift before deciding
whether the YAML or the live state is wrong. All fixes still flow through YAML + Terraform —
never mutate GitHub directly.
