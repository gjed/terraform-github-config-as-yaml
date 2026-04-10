output "team_id" {
  description = "The ID of the team (used as parent_team_id by child teams)"
  value       = github_team.this.id
}

output "team_slug" {
  description = "The slug of the team"
  value       = github_team.this.slug
}
