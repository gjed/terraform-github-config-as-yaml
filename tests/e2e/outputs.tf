output "repositories" {
  description = "Map of managed repositories with their URLs"
  value       = module.github_org.repositories
}

output "repository_count" {
  description = "Total number of managed repositories"
  value       = module.github_org.repository_count
}

output "organization" {
  description = "GitHub organization being managed"
  value       = module.github_org.organization
}

output "subscription_tier" {
  description = "GitHub subscription tier"
  value       = module.github_org.subscription_tier
}

output "subscription_warnings" {
  description = "Warnings about features unavailable on current subscription tier"
  value       = module.github_org.subscription_warnings
}

output "skipped_org_rulesets" {
  description = "Org rulesets skipped because the subscription tier does not support them"
  value       = module.github_org.skipped_org_rulesets
}

output "duplicate_key_warnings" {
  description = "Warnings about duplicate keys in config files"
  value       = module.github_org.duplicate_key_warnings
}

output "managed_members" {
  description = "Map of organization members managed by Terraform"
  value       = module.github_org.managed_members
}

output "managed_member_count" {
  description = "Total number of organization members managed by Terraform"
  value       = module.github_org.managed_member_count
}

output "managed_teams" {
  description = "Map of managed team slugs to their IDs"
  value       = module.github_org.managed_teams
}

output "team_count" {
  description = "Total number of managed teams"
  value       = module.github_org.team_count
}

output "org_webhooks" {
  description = "Map of organization webhook names to their URLs"
  sensitive   = true
  value       = module.github_org.org_webhooks
}

output "security_manager_teams" {
  description = "List of team slugs assigned the security_manager organization role"
  value       = module.github_org.security_manager_teams
}

output "organization_settings_warnings" {
  description = "Warnings about enterprise-only organization settings skipped on current subscription tier"
  value       = module.github_org.organization_settings_warnings
}
