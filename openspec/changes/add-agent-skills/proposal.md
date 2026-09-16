## Why

Agents working on this repo (or on a consumer's fork) repeatedly need the same operational
knowledge: how repository YAML merges across groups, how to review a plan for destructive
changes, how rulesets and tier gating behave, and how onboarding/offboarding scripts are used.
Today that knowledge lives only in AGENTS.md prose and script headers. Shipping it as
vendor-agnostic Agent Skills makes it discoverable and executable by any agent client, and a
committed `.mcp.json` gives every clone the same optional, read-only MCP tooling.

## What Changes

- Add consumer-facing skills under `skills/`: `manage-repo-config`, `plan-safety-review`,
  `ruleset-authoring`, `onboard-offboard`. These cover only the published module contract
  (YAML config, module variables, shipped scripts).
- Add maintainer-only skills under `skills/internal/`: `e2e-testing`, `openspec-workflow`.
  Kept separate so consumers' agents are not triggered by repo-internal workflows.
- Add `.mcp.json` at the repo root declaring two optional stdio servers:
  `hashicorp/terraform-mcp-server` (anonymous registry doc/schema lookup) and
  `ghcr.io/github/github-mcp-server` in read-only mode reusing the existing `GITHUB_TOKEN`.
  No new credentials; servers are optional and skills degrade gracefully without them.
- Skills follow the open Agent Skills format (`SKILL.md` with `name`/`description`
  frontmatter) so they work across agent clients without vendor lock-in.

## Capabilities

### New Capabilities

- `agent-tooling`: vendor-agnostic agent skills and optional MCP server declarations shipped
  with the repository.

## Impact

- New: `skills/` (4 consumer skills), `skills/internal/` (2 maintainer skills), `.mcp.json`
- No Terraform, script, or config behavior changes; documentation/tooling only
