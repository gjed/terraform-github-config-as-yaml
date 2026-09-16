## ADDED Requirements

### Requirement: Vendor-agnostic agent skills

The repository SHALL ship agent skills as directories containing a `SKILL.md` file with YAML
frontmatter (`name`, `description`) followed by markdown instructions, per the open Agent
Skills format. Skills SHALL NOT depend on any specific agent vendor, client, or runtime.

#### Scenario: Skill file format

- **WHEN** an agent client loads a directory under `skills/`
- **THEN** it finds a `SKILL.md` with `name` and `description` frontmatter and markdown body

### Requirement: Consumer and maintainer skills are separated

Consumer-facing skills (covering only the published module contract: YAML configuration,
module variables, and shipped scripts) SHALL live directly under `skills/`. Maintainer-only
skills (repo-internal workflows such as e2e testing and openspec) SHALL live under
`skills/internal/`.

#### Scenario: Consumer skill placement

- **WHEN** a skill documents editing `config/repository/*.yml` or reviewing a plan
- **THEN** it is located directly under `skills/`

#### Scenario: Maintainer skill placement

- **WHEN** a skill documents `make e2e-*` targets or the openspec change workflow
- **THEN** it is located under `skills/internal/`

### Requirement: Optional MCP server declaration

The repository SHALL include a `.mcp.json` at the root declaring optional stdio MCP servers
for Terraform Registry documentation lookup and read-only GitHub inspection. The GitHub
server SHALL reuse the `GITHUB_TOKEN` environment variable via expansion (no committed
credentials) and SHALL be configured read-only. Skills MAY reference these servers but SHALL
remain functional when the servers are absent.

#### Scenario: No new credentials required

- **WHEN** a user clones the repository without configuring anything beyond `GITHUB_TOKEN`
- **THEN** `.mcp.json` contains no literal secrets and the GitHub server resolves its token
  from the environment

#### Scenario: Skills degrade gracefully

- **WHEN** an agent uses a skill and the declared MCP servers are not running
- **THEN** the skill's workflow still completes using terraform/gh CLI or web lookup
