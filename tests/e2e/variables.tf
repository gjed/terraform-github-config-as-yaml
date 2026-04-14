variable "github_org" {
  description = "GitHub organization name to provision e2e test resources into. Use a dedicated throwaway test org."
  type        = string
}

variable "webhook_secret" {
  description = "Secret value for the e2e-webhook. Can be any string; webhook.site ignores secrets."
  type        = string
  sensitive   = true
  default     = "e2e-test-secret"
}

variable "membership_management_enabled" {
  description = <<-EOT
    Enable organization membership management for e2e testing.
    Defaults to false for safety. To test membership features, set to true and
    add a real GitHub username to config/membership/test-members.yml.
  EOT
  type        = bool
  default     = false
}
