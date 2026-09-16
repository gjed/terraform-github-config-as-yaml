# Agent Skills

Skills for AI coding agents working with this Terraform module, in the vendor-neutral
[Agent Skills](https://agentskills.io) format (`<skill>/SKILL.md`). Any client that supports
the format (Claude Code, opencode, Cursor, Codex adapters) can load them.

## Layout

- `consumer/` — for users of the published module (`gjed/config-as-yaml/github`) managing their
  own organization. These skills only rely on the consumer contract: YAML config, module
  variables, and the scripts shipped with the module.
- `maintainer/` — for maintainers of this repository only. Do not load these when consuming the
  module; they reference internal workflows (e2e fixtures, openspec) that do not apply.

## Consumer skills

| Skill | Purpose |
| ----- | ------- |
| `manage-repo-config` | Add, modify, or remove repositories in `config/` YAML |
| `plan-safety-review` | Review a saved Terraform plan for destructive or risky changes |
| `ruleset-authoring` | Author repository and organization rulesets with tier gating |
| `onboard-offboard` | Import existing repositories or remove repositories from management |

## Maintainer skills

| Skill | Purpose |
| ----- | ------- |
| `e2e-testing` | Run the end-to-end test fixture lifecycle |
| `openspec-workflow` | Follow the mandatory openspec change process |

## Optional MCP servers

The repository root ships a `.mcp.json` declaring two optional, read-only MCP servers that
sharpen these skills. Neither is required — every skill degrades gracefully without them.

- `terraform` ([hashicorp/terraform-mcp-server](https://github.com/hashicorp/terraform-mcp-server)):
  live Terraform Registry doc/schema lookup for the pinned `integrations/github` provider
  version. No credentials needed.
- `github` ([github/github-mcp-server](https://github.com/github/github-mcp-server)): read-only
  inspection of live GitHub state. Reuses the `GITHUB_TOKEN` this module already requires
  (see `.env.example`); runs with `GITHUB_READ_ONLY=1` so all mutations still flow through
  Terraform.
