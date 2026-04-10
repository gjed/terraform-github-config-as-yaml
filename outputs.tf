# Output values for managed resources

output "repositories" {
  description = "Map of managed repositories with their URLs"
  value = {
    for repo_name, repo in module.repositories : repo_name => {
      name       = repo.name
      url        = repo.html_url
      ssh_url    = repo.ssh_clone_url
      visibility = repo.visibility
    }
  }
}

output "repository_count" {
  description = "Total number of managed repositories"
  value       = length(module.repositories)
}

output "organization" {
  description = "GitHub organization being managed"
  value       = local.github_org
}

output "subscription_tier" {
  description = "GitHub subscription tier"
  value       = local.subscription
}

# Output warning when rulesets are skipped due to subscription tier
output "subscription_warnings" {
  description = "Warnings about features unavailable on current subscription tier"
  value = length(local.repos_with_skipped_rulesets) > 0 ? {
    message = "Rulesets skipped for ${length(local.repos_with_skipped_rulesets)} private repo(s) - requires paid GitHub plan"
    repos   = local.repos_with_skipped_rulesets
    tier    = local.subscription
  } : null
}

output "managed_members" {
  description = "Map of organization members managed by Terraform, keyed by username with their role"
  value = {
    for username, membership in github_membership.this :
    username => {
      username = membership.username
      role     = membership.role
    }
  }
}

output "managed_member_count" {
  description = "Total number of organization members managed by Terraform"
  value       = length(github_membership.this)
}

# Output warning when org rulesets are skipped due to subscription tier
output "skipped_org_rulesets" {
  description = "Org rulesets skipped because the subscription tier (free/pro) does not support them"
  value = length(local.skipped_org_ruleset_names) > 0 ? {
    message  = "Organization rulesets skipped - requires team or enterprise GitHub plan"
    rulesets = local.skipped_org_ruleset_names
    tier     = local.subscription
  } : null
}

# Output warning when duplicate keys are detected across config files
# Duplicates cause shallow merge - the entire definition from the later file wins
output "duplicate_key_warnings" {
  description = "Warnings about duplicate keys in config files (shallow merge - later file wins entirely)"
  value = (
    length(local.duplicate_repository_keys) > 0 ||
    length(local.duplicate_group_keys) > 0 ||
    length(local.duplicate_ruleset_keys) > 0 ||
    length(local.duplicate_membership_keys) > 0
    ) ? {
    message = "WARNING: Duplicate keys detected across config files. Later files (alphabetically) completely override earlier ones - no deep merge!"
    repositories = length(local.duplicate_repository_keys) > 0 ? {
      for key, files in local.duplicate_repository_keys :
      key => "defined in: ${join(", ", files)} - using: ${files[length(files) - 1]}"
    } : null
    groups = length(local.duplicate_group_keys) > 0 ? {
      for key, files in local.duplicate_group_keys :
      key => "defined in: ${join(", ", files)} - using: ${files[length(files) - 1]}"
    } : null
    rulesets = length(local.duplicate_ruleset_keys) > 0 ? {
      for key, files in local.duplicate_ruleset_keys :
      key => "defined in: ${join(", ", files)} - using: ${files[length(files) - 1]}"
    } : null
    members = length(local.duplicate_membership_keys) > 0 ? {
      for key, files in local.duplicate_membership_keys :
      key => "defined in: ${join(", ", files)} - using: ${files[length(files) - 1]}"
    } : null
  } : null
}

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
  description = "Total number of managed teams (0 when is_organization is false)"
  value       = local.is_organization ? length(local.all_teams) : 0
}
