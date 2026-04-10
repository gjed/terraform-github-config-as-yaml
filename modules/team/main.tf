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
