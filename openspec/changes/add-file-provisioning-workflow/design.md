## Context

Terraform's GitHub provider creates commits using the configured authentication token, but these commits
are not GPG-signed. Many organizations enforce signed commit requirements on protected branches, which
causes Terraform file provisioning to fail or bypass protection rules.

**Stakeholders:**

- Repository administrators who need consistent file provisioning
- Security teams requiring signed commits
- DevOps teams managing Terraform automation

## Goals / Non-Goals

**Goals:**

- Enable file provisioning that works with signed commit requirements
- Provide a reviewable workflow for provisioned changes
- Support both manual and automated PR creation
- Maintain audit trail for provisioned file changes

**Non-Goals:**

- Implementing GPG signing in Terraform (not supported by provider)
- Replacing existing `github_repository_file` behavior for users without signed commit requirements
- Managing GitHub Actions workflows within target repositories (out of scope per project constraints)

## Decisions

### Decision: Branch-based provisioning strategy

**What:** Terraform provisions files to a dedicated branch, not directly to protected branches.

**Why:** This approach:

1. Avoids signed commit conflicts - the provisioning branch can be unprotected
1. Enables PR-based review of provisioned content
1. Allows GitHub Actions to create signed commits when merging
1. Works with any branch protection configuration

**Alternatives considered:**

- **GitHub App with signing capability**: Requires additional infrastructure, app registration, and
  key management. More complex for template users.
- **Direct file provisioning with protection bypass**: Security risk, not recommended.
- **External CI/CD for file management**: Moves logic outside Terraform, loses IaC benefits.

### Decision: Optional GitHub Action for PR creation

**What:** Provide a reusable workflow that users can install to automate PR creation.

**Why:** Not all users need automated PR creation. Some may prefer manual review triggers or have
existing automation. Making it optional:

1. Reduces setup complexity for simple use cases
1. Allows customization of PR workflow
1. Supports orgs with existing PR automation

### Decision: Configuration inheritance for provisioning settings

**What:** Provisioning settings follow the same inheritance model as other configuration:
`config.yml` -> `groups` -> `repository`

**Why:** Consistency with existing patterns. Users can set org-wide defaults and override per-repo.

## Risks / Trade-offs

| Risk                                     | Mitigation                                                         |
| ---------------------------------------- | ------------------------------------------------------------------ |
| Branch divergence if PRs not merged      | Document best practices; consider staleness warnings               |
| Complexity increase for simple use cases | Make PR workflow optional; direct provisioning still works         |
| Race conditions with manual changes      | Document provisioning branch as managed; use clear commit messages |

## Migration Plan

1. **Phase 1**: Add provisioning configuration schema (backwards compatible)
1. **Phase 2**: Implement branch-based provisioning for new files
1. **Phase 3**: Provide migration guide for existing `github_repository_file` users
1. **Rollback**: Provisioning can be disabled per-repository; no destructive changes

## Open Questions

- Should we support multiple provisioning branches per repository for different file categories?
- Should the PR workflow support auto-merge for certain file types (e.g., LICENSE)?
- How to handle conflicts between provisioning branch and default branch?
