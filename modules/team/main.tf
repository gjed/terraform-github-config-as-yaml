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
# Only created when review_request_delegation is provided AND enabled is true
# Note: the GitHub provider does not support a "disabled" delegation state via HCL;
# setting enabled = false removes the resource, which is the closest approximation.
resource "github_team_settings" "this" {
  # coalesce guards against an explicit `enabled: null` in YAML, which bypasses
  # the optional() default and would otherwise cause a type error in the condition.
  count = (var.review_request_delegation != null && coalesce(var.review_request_delegation.enabled, true)) ? 1 : 0

  team_id = github_team.this.id

  review_request_delegation {
    # coalesce(try(...)) guards against fields explicitly set to null in YAML,
    # which bypasses optional() defaults and would fail at plan/apply time.
    algorithm    = coalesce(try(var.review_request_delegation.algorithm, null), "round_robin")
    member_count = coalesce(try(var.review_request_delegation.member_count, null), 1)
    notify       = coalesce(try(var.review_request_delegation.notify, null), true)
  }
}
