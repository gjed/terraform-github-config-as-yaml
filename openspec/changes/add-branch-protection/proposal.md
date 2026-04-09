# Change: Add Branch Protection

## Why

The module currently supports only repository rulesets (`github_repository_ruleset`) for branch
policy enforcement. Traditional branch protection rules (`github_branch_protection`) offer a
different feature set — including `restrict_pushes`, `lock_branch`,
`require_conversation_resolution`, and fine-grained dismissal restrictions — that rulesets do not
cover. Additionally, branch protection works on all subscription tiers for private repos, unlike
rulesets on the free tier.

Users need the ability to define both rulesets and branch protection rules on the same repository,
each serving its own purpose.

## What Changes

- Add `config/branch-protection/` directory for named branch protection definitions
- Groups and repositories reference protections via `branch_protections: [name1, name2]`
- Merging follows the same semantics as rulesets: collected from groups in order, repo-specific
  appended, deduplicated by name
- New `github_branch_protection` resource in `modules/repository/main.tf`
- Full coverage of the `github_branch_protection` resource: required reviews, status checks,
  push restrictions, force push/deletion controls, conversation resolution, lock branch, signed
  commits, linear history, and admin enforcement
- Both rulesets and branch protections can coexist on the same repository

## Impact

- Affected specs: `repository-management`
- Affected code: `yaml-config.tf` (loading, merging, validation), `modules/repository/main.tf`
  (new resource), `modules/repository/variables.tf` (new variable), `main.tf` (pass-through)
- New directory: `config/branch-protection/`
- New example file: `config/branch-protection/default-protections.yml`
- Backward compatible: existing rulesets and all other configuration continue to work unchanged
