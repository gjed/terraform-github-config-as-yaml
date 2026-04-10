# Add GitHub Teams Management — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable managing GitHub Teams (creation, membership, settings) via YAML configuration
in `config/team/`, following the same patterns as repositories, groups, and rulesets.

**Architecture:** Teams are defined in nested YAML under `config/team/*.yml`. The `yaml-config.tf`
layer loads, flattens the nested hierarchy into a tier-classified flat map, and feeds three tiered
module invocations in `main.tf` (`teams_root`, `teams_level_1`, `teams_level_2`). A new
`modules/team/` submodule manages `github_team`, `github_team_membership`, and
`github_team_settings` resources.

**Tech Stack:** Terraform >= 1.0, GitHub Provider ~> 6.0, Python 3.x (validation script)

---

## File Structure

| File | Action | Responsibility |
| --- | --- | --- |
| `modules/team/main.tf` | Create | `github_team`, `github_team_membership`, `github_team_settings` resources |
| `modules/team/variables.tf` | Create | Input variables for team module |
| `modules/team/outputs.tf` | Create | Team ID and slug outputs |
| `yaml-config.tf` | Modify | Team config loading, nested flattening, tier classification, validation |
| `main.tf` | Modify | Three tiered team module invocations |
| `outputs.tf` | Modify | Team-related outputs |
| `config/team/.gitkeep` | Create | Empty team directory placeholder for template |
| `examples/consumer/config/team/.gitkeep` | Create | Empty team directory placeholder for consumer example |
| `scripts/validate-config.py` | Modify | Team schema validation, cross-reference warnings |

---

### Task 1: Create the Team Submodule — Variables and Outputs

**Files:**

- Create: `modules/team/variables.tf`
- Create: `modules/team/outputs.tf`

- [x] **Step 1: Create `modules/team/variables.tf`**

```hcl
variable "name" {
  description = "Team name (used as the team slug)"
  type        = string
}

variable "description" {
  description = "Team description"
  type        = string
}

variable "privacy" {
  description = "Team privacy level: closed (visible to org) or secret (only visible to members)"
  type        = string
  default     = "closed"

  validation {
    condition     = contains(["closed", "secret"], var.privacy)
    error_message = "Privacy must be 'closed' or 'secret'."
  }
}

variable "parent_team_id" {
  description = "ID of the parent team (null for root teams)"
  type        = string
  default     = null
}

variable "members" {
  description = "List of GitHub usernames to add as team members"
  type        = list(string)
  default     = []
}

variable "maintainers" {
  description = "List of GitHub usernames to add as team maintainers"
  type        = list(string)
  default     = []
}

variable "review_request_delegation" {
  description = "PR review request delegation settings"
  type = object({
    enabled      = bool
    algorithm    = optional(string, "round_robin")
    member_count = optional(number, 1)
    notify       = optional(bool, true)
  })
  default = null

  validation {
    condition     = var.review_request_delegation == null || contains(["round_robin", "load_balance"], coalesce(var.review_request_delegation.algorithm, "round_robin"))
    error_message = "Algorithm must be 'round_robin' or 'load_balance'."
  }
}
```

- [x] **Step 2: Create `modules/team/outputs.tf`**

```hcl
output "team_id" {
  description = "The ID of the team (used as parent_team_id by child teams)"
  value       = github_team.this.id
}

output "team_slug" {
  description = "The slug of the team"
  value       = github_team.this.slug
}
```

- [x] **Step 3: Commit**

```bash
git add modules/team/variables.tf modules/team/outputs.tf
git commit -m "feat(team): add team submodule variables and outputs"
```

---

### Task 2: Create the Team Submodule — Resources

**Files:**

- Create: `modules/team/main.tf`

- [x] **Step 1: Create `modules/team/main.tf`**

```hcl
terraform {
  required_version = ">= 1.0"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
}

resource "github_team" "this" {
  name           = var.name
  description    = var.description
  privacy        = var.privacy
  parent_team_id = var.parent_team_id
}

# Manage team members
resource "github_team_membership" "members" {
  for_each = toset(var.members)

  team_id  = github_team.this.id
  username = each.value
  role     = "member"
}

# Manage team maintainers
resource "github_team_membership" "maintainers" {
  for_each = toset(var.maintainers)

  team_id  = github_team.this.id
  username = each.value
  role     = "maintainer"
}

# Manage PR review request delegation settings
# Only created when review_request_delegation is provided
resource "github_team_settings" "this" {
  count = var.review_request_delegation != null ? 1 : 0

  team_id = github_team.this.id

  review_request_delegation {
    algorithm    = var.review_request_delegation.algorithm
    member_count = var.review_request_delegation.member_count
    notify       = var.review_request_delegation.notify
  }
}
```

- [x] **Step 2: Run `terraform fmt` on the module**

Run: `terraform fmt modules/team/`

Expected: Files formatted (or no changes if already correct).

- [x] **Step 3: Run `terraform validate` on the module**

Run: `cd modules/team && terraform init -backend=false && terraform validate`

Expected: `Success! The configuration is valid.`

Note: This validates syntax and structure. The actual resources require a GitHub provider
connection at apply time.

- [x] **Step 4: Commit**

```bash
git add modules/team/main.tf
git commit -m "feat(team): add team submodule resources

Implements github_team, github_team_membership, and
github_team_settings resources in modules/team/."
```

---

### Task 3: Add Team Config Loading to `yaml-config.tf`

**Files:**

- Modify: `yaml-config.tf` (add team config loading and flattening logic at the end of the
  `locals` block, before the `check` blocks)
- Create: `config/team/.gitkeep`

- [x] **Step 1: Create the empty team config directory**

```bash
touch config/team/.gitkeep
```

- [x] **Step 2: Add team config path and file loading to `yaml-config.tf`**

Add the following after the existing `webhook_dir` / `webhook_files` / `webhooks_config` block
(around line 121), inside the same `locals` block:

```hcl
  # Load team definitions from config/team/ directory
  # Directory is optional - missing directory results in empty map
  team_dir = "${local.config_base_path}/team"
  team_files = try(
    fileset(local.team_dir, "*.yml"),
    toset([])
  )
  teams_config_raw = merge([
    for f in sort(tolist(local.team_files)) :
    try(yamldecode(file("${local.team_dir}/${f}")), {})
  ]...)
```

- [x] **Step 3: Add the nested team flattening logic**

Add below the `teams_config_raw` local. This walks up to 3 levels of nesting and produces a flat
map with tier classification.

```hcl
  # Flatten nested team hierarchy into a tiered flat map
  # Input: nested YAML where child teams are under parent's `teams` key
  # Output: flat map of slug => { description, privacy, members, maintainers,
  #          review_request_delegation, parent_slug, tier }
  #
  # Tier 0: root teams (no parent)
  # Tier 1: children of tier 0
  # Tier 2: children of tier 1 (max depth)

  # Tier 0 - root level teams
  tier_0_teams = {
    for slug, config in local.teams_config_raw : slug => {
      name                      = slug
      description               = config.description
      privacy                   = lookup(config, "privacy", "closed")
      members                   = lookup(config, "members", [])
      maintainers               = lookup(config, "maintainers", [])
      review_request_delegation = lookup(config, "review_request_delegation", null)
      parent_slug               = null
      tier                      = 0
    }
  }

  # Tier 1 - children of root teams
  tier_1_teams = merge([
    for parent_slug, parent_config in local.teams_config_raw : {
      for child_slug, child_config in lookup(parent_config, "teams", {}) : child_slug => {
        name                      = child_slug
        description               = child_config.description
        privacy                   = lookup(child_config, "privacy", "closed")
        members                   = lookup(child_config, "members", [])
        maintainers               = lookup(child_config, "maintainers", [])
        review_request_delegation = lookup(child_config, "review_request_delegation", null)
        parent_slug               = parent_slug
        tier                      = 1
      }
    }
  ]...)

  # Tier 2 - grandchildren (children of tier 1)
  tier_2_teams = merge([
    for parent_slug, parent_config in local.teams_config_raw : merge([
      for child_slug, child_config in lookup(parent_config, "teams", {}) : {
        for grandchild_slug, grandchild_config in lookup(child_config, "teams", {}) : grandchild_slug => {
          name                      = grandchild_slug
          description               = grandchild_config.description
          privacy                   = lookup(grandchild_config, "privacy", "closed")
          members                   = lookup(grandchild_config, "members", [])
          maintainers               = lookup(grandchild_config, "maintainers", [])
          review_request_delegation = lookup(grandchild_config, "review_request_delegation", null)
          parent_slug               = child_slug
          tier                      = 2
        }
      }
    ]...)
  ]...)

  # Combined flat map of all teams (for validation and outputs)
  all_teams = merge(local.tier_0_teams, local.tier_1_teams, local.tier_2_teams)
```

- [x] **Step 4: Add team validation checks**

Add a new `check` block after the existing `check "template_references"` block at the bottom of
`yaml-config.tf`:

```hcl
# Validate no duplicate team slugs across tiers
check "team_slug_uniqueness" {
  assert {
    condition = (
      length(local.all_teams) ==
      length(local.tier_0_teams) + length(local.tier_1_teams) + length(local.tier_2_teams)
    )
    error_message = "Duplicate team slugs detected across hierarchy levels. Each team slug must be unique."
  }
}

# Validate no user appears in both members and maintainers for any team
check "team_member_maintainer_overlap" {
  assert {
    condition = length([
      for slug, team in local.all_teams : slug
      if length(setintersection(toset(team.members), toset(team.maintainers))) > 0
    ]) == 0
    error_message = "Some teams have users in both members and maintainers. A user can only have one role per team."
  }
}

# Validate no teams nested deeper than 3 levels
# This checks that tier 2 teams have no nested `teams` key with content
check "team_nesting_depth" {
  assert {
    condition = length(flatten([
      for parent_slug, parent_config in local.teams_config_raw : flatten([
        for child_slug, child_config in lookup(parent_config, "teams", {}) : [
          for grandchild_slug, grandchild_config in lookup(child_config, "teams", {}) :
          grandchild_slug
          if length(lookup(grandchild_config, "teams", {})) > 0
        ]
      ])
    ])) == 0
    error_message = "Team nesting exceeds maximum depth of 3 levels. Reorganize your team hierarchy."
  }
}
```

- [x] **Step 5: Run `terraform fmt`**

Run: `terraform fmt yaml-config.tf`

Expected: File formatted.

- [x] **Step 6: Commit**

```bash
git add yaml-config.tf config/team/.gitkeep
git commit -m "feat(team): add team config loading and hierarchy flattening

Loads team YAML from config/team/, flattens nested hierarchy into
three tiers, and validates slug uniqueness and nesting depth."
```

---

### Task 4: Wire Team Modules in `main.tf`

**Files:**

- Modify: `main.tf`

- [x] **Step 1: Add tiered team module invocations to `main.tf`**

Add after the existing `github_actions_organization_workflow_permissions` resource block (after
line 101):

```hcl
# Manage GitHub Teams - Tier 0 (root teams, no parent)
# Only created for organizations (teams are not available for personal accounts)
module "teams_root" {
  source = "./modules/team"

  for_each = local.is_organization ? local.tier_0_teams : {}

  name        = each.value.name
  description = each.value.description
  privacy     = each.value.privacy
  members     = each.value.members
  maintainers = each.value.maintainers

  review_request_delegation = each.value.review_request_delegation
}

# Manage GitHub Teams - Tier 1 (children of root teams)
module "teams_level_1" {
  source = "./modules/team"

  for_each = local.is_organization ? local.tier_1_teams : {}

  name           = each.value.name
  description    = each.value.description
  privacy        = each.value.privacy
  parent_team_id = module.teams_root[each.value.parent_slug].team_id
  members        = each.value.members
  maintainers    = each.value.maintainers

  review_request_delegation = each.value.review_request_delegation
}

# Manage GitHub Teams - Tier 2 (grandchildren, max depth)
module "teams_level_2" {
  source = "./modules/team"

  for_each = local.is_organization ? local.tier_2_teams : {}

  name           = each.value.name
  description    = each.value.description
  privacy        = each.value.privacy
  parent_team_id = module.teams_level_1[each.value.parent_slug].team_id
  members        = each.value.members
  maintainers    = each.value.maintainers

  review_request_delegation = each.value.review_request_delegation
}
```

- [x] **Step 2: Run `terraform fmt`**

Run: `terraform fmt main.tf`

Expected: File formatted.

- [x] **Step 3: Commit**

```bash
git add main.tf
git commit -m "feat(team): wire tiered team modules in main.tf

Adds three module invocations (teams_root, teams_level_1,
teams_level_2) with dependency ordering for parent-child teams.
Guarded by is_organization flag."
```

---

### Task 5: Add Team Outputs

**Files:**

- Modify: `outputs.tf`

- [x] **Step 1: Add team outputs to `outputs.tf`**

Add at the end of the file:

```hcl
output "managed_teams" {
  description = "Map of managed team slugs to their IDs"
  value = merge(
    {
      for slug, team in module.teams_root : slug => {
        id   = team.team_id
        slug = team.team_slug
      }
    },
    {
      for slug, team in module.teams_level_1 : slug => {
        id   = team.team_id
        slug = team.team_slug
      }
    },
    {
      for slug, team in module.teams_level_2 : slug => {
        id   = team.team_id
        slug = team.team_slug
      }
    }
  )
}

output "team_count" {
  description = "Total number of managed teams"
  value       = length(local.all_teams)
}
```

- [x] **Step 2: Run `terraform fmt`**

Run: `terraform fmt outputs.tf`

Expected: File formatted.

- [x] **Step 3: Commit**

```bash
git add outputs.tf
git commit -m "feat(team): add managed_teams and team_count outputs"
```

---

### Task 6: Update Validation Script

**Files:**

- Modify: `scripts/validate-config.py`

- [x] **Step 1: Add team directory constant and valid values**

At the top of `scripts/validate-config.py`, after the existing directory constants (line 19),
add:

```python
TEAM_DIR = CONFIG_DIR / "team"
```

After `VALID_RULE_TYPES` (around line 37), add:

```python
VALID_TEAM_PRIVACIES = ["closed", "secret"]
VALID_DELEGATION_ALGORITHMS = ["round_robin", "load_balance"]
```

- [x] **Step 2: Add `validate_teams` function**

Add after the existing `validate_rulesets` function (after line 204):

```python
def flatten_teams(teams: dict, depth: int = 0, parent: str = None) -> list[dict]:
    """Recursively flatten nested team definitions."""
    result = []
    for slug, config in teams.items():
        if not isinstance(config, dict):
            continue
        result.append({
            "slug": slug,
            "config": config,
            "depth": depth,
            "parent": parent,
        })
        # Recurse into nested teams
        nested = config.get("teams", {})
        if isinstance(nested, dict) and nested:
            result.extend(flatten_teams(nested, depth + 1, slug))
    return result


def validate_teams(teams: dict) -> tuple[list[str], list[str]]:
    """Validate teams configuration. Returns (errors, warnings)."""
    errors = []
    warnings = []

    if not teams:
        return errors, warnings

    flat = flatten_teams(teams)

    # Check for duplicate slugs
    slugs = [t["slug"] for t in flat]
    seen = set()
    for slug in slugs:
        if slug in seen:
            errors.append(f"teams: Duplicate team slug '{slug}' found across hierarchy")
        seen.add(slug)

    # Check max nesting depth
    for team in flat:
        if team["depth"] > 2:
            errors.append(
                f"teams: Team '{team['slug']}' exceeds maximum nesting depth of 3 levels "
                f"(depth {team['depth'] + 1})"
            )

    # Validate each team's fields
    for team in flat:
        slug = team["slug"]
        config = team["config"]

        if "description" not in config:
            errors.append(f"teams: Team '{slug}' missing required field 'description'")

        privacy = config.get("privacy")
        if privacy and privacy not in VALID_TEAM_PRIVACIES:
            errors.append(
                f"teams: Team '{slug}' has invalid privacy '{privacy}'. "
                f"Valid values: {', '.join(VALID_TEAM_PRIVACIES)}"
            )

        # Validate no overlap between members and maintainers
        members = set(config.get("members", []))
        maintainers = set(config.get("maintainers", []))
        overlap = members & maintainers
        if overlap:
            errors.append(
                f"teams: Team '{slug}' has users in both members and maintainers: "
                f"{', '.join(sorted(overlap))}"
            )

        # Validate review_request_delegation
        delegation = config.get("review_request_delegation")
        if isinstance(delegation, dict):
            if "enabled" not in delegation:
                errors.append(
                    f"teams: Team '{slug}' review_request_delegation missing "
                    f"required field 'enabled'"
                )
            algorithm = delegation.get("algorithm")
            if algorithm and algorithm not in VALID_DELEGATION_ALGORITHMS:
                errors.append(
                    f"teams: Team '{slug}' has invalid delegation algorithm '{algorithm}'. "
                    f"Valid values: {', '.join(VALID_DELEGATION_ALGORITHMS)}"
                )

    return errors, warnings
```

- [x] **Step 3: Add team cross-reference warning function**

Add after `validate_teams`:

```python
def check_team_cross_references(
    repos: dict, groups: dict, managed_team_slugs: set
) -> list[str]:
    """Warn when repos/groups reference team slugs not in config/team/."""
    warnings = []

    if not managed_team_slugs:
        return warnings

    # Collect all referenced team slugs from repos and groups
    referenced = set()
    for repo_name, repo_config in repos.items():
        if isinstance(repo_config, dict):
            for slug in repo_config.get("teams", {}).keys():
                referenced.add((slug, f"repository '{repo_name}'"))

    for group_name, group_config in groups.items():
        if isinstance(group_config, dict):
            for slug in group_config.get("teams", {}).keys():
                referenced.add((slug, f"group '{group_name}'"))

    for slug, source in referenced:
        if slug not in managed_team_slugs:
            warnings.append(
                f"teams: {source} references team '{slug}' which is not defined in "
                f"config/team/ (may be managed externally)"
            )

    return warnings
```

- [x] **Step 4: Update `main()` to call team validation**

In the `main()` function, after the block that loads rulesets (around line 259), add team
loading:

```python
        # Load teams (optional directory)
        if TEAM_DIR.exists():
            teams = load_yaml_directory(TEAM_DIR)
        else:
            teams = {}
```

After the existing validation calls (around line 268), add:

```python
    team_errors, team_warnings = validate_teams(teams)
    all_errors.extend(team_errors)
```

After the team validation, add cross-reference check:

```python
    # Cross-reference check for team slugs (warnings only)
    if teams:
        flat_teams = flatten_teams(teams)
        managed_slugs = {t["slug"] for t in flat_teams}
        team_xref_warnings = check_team_cross_references(repos, groups, managed_slugs)
```

In the success output section (around line 286), add team count and warnings:

```python
        print(f"  - Teams: {len(flatten_teams(teams)) if teams else 0}")
```

Before the final `sys.exit(0)`, add warning output:

```python
        # Print warnings (non-fatal)
        all_warnings = team_warnings
        if teams:
            all_warnings.extend(team_xref_warnings)
        if all_warnings:
            print()
            print("Warnings:")
            for warning in all_warnings:
                print(f"  - {warning}")
```

- [x] **Step 5: Run the validation script to verify it works with no teams**

Run: `python scripts/validate-config.py`

Expected: `Validation PASSED` with `Teams: 0` in the output.

- [x] **Step 6: Commit**

```bash
git add scripts/validate-config.py
git commit -m "feat(team): add team validation to validate-config.py

Validates team schema, nesting depth, duplicate slugs, membership
overlap, delegation settings, and cross-reference warnings."
```

---

### Task 7: Add Consumer Example Placeholder

**Files:**

- Create: `examples/consumer/config/team/.gitkeep`

- [x] **Step 1: Create the team directory in the consumer example**

```bash
touch examples/consumer/config/team/.gitkeep
```

- [x] **Step 2: Commit**

```bash
git add examples/consumer/config/team/.gitkeep
git commit -m "chore(example): add empty team config directory to consumer example"
```

---

### Task 8: Run Full Validation

- [x] **Step 1: Run `terraform fmt` on the whole project**

Run: `terraform fmt -recursive .`

Expected: All files formatted or already correct.

- [x] **Step 2: Run `terraform validate`**

Run: `terraform validate`

Expected: `Success! The configuration is valid.`

Note: This requires `terraform init` to have been run. If providers aren't initialized,
run `terraform init -backend=false` first.

- [x] **Step 3: Run the validation script**

Run: `python scripts/validate-config.py`

Expected: `Validation PASSED` with `Teams: 0`.

- [x] **Step 4: Run pre-commit hooks**

Run: `source .venv/bin/activate && pre-commit run --all-files`

Expected: All checks pass. Fix any formatting issues flagged.

- [x] **Step 5: If any fixes were needed, commit them**

```bash
git add -A
git commit -m "style: fix formatting from pre-commit hooks"
```

---

### Task 9: Commit OpenSpec Artifacts

- [x] **Step 1: Stage and commit all OpenSpec change files**

```bash
git add openspec/changes/add-github-teams-management/
git commit -m "feat(spec): add github-teams-management change proposal

Adds OpenSpec change proposal for issue #27: GitHub Teams management.
Includes proposal, design, spec, and implementation tasks."
```
