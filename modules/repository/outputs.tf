output "name" {
  description = "Repository name"
  value       = github_repository.this.name
}

output "full_name" {
  description = "Full repository name (org/repo)"
  value       = github_repository.this.full_name
}

output "html_url" {
  description = "Repository URL"
  value       = github_repository.this.html_url
}

output "ssh_clone_url" {
  description = "SSH clone URL"
  value       = github_repository.this.ssh_clone_url
}

output "http_clone_url" {
  description = "HTTP clone URL"
  value       = github_repository.this.http_clone_url
}

output "visibility" {
  description = "Repository visibility"
  value       = github_repository.this.visibility
}

output "repo_id" {
  description = "Repository ID"
  value       = github_repository.this.repo_id
}

# Names only - secret and variable values are never exposed as outputs
output "secret_names" {
  description = "Names of managed repository Actions and Dependabot secrets"
  value = {
    actions    = keys(github_actions_secret.this)
    dependabot = keys(github_dependabot_secret.this)
  }
}

output "variable_names" {
  description = "Names of managed repository Actions variables"
  value       = keys(github_actions_variable.this)
}

output "webhooks" {
  description = "Map of webhook names to their URLs"
  value = {
    for name, webhook in github_repository_webhook.this : name => webhook.url
  }
}
