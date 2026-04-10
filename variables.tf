# Variables for the GitHub org Terraform module

variable "config_path" {
  description = "Absolute path to the directory containing config.yml, group/, repository/, ruleset/, and webhook/ subdirectories. Consumers should set this to path.root + \"/config\". Must be a static string - computed values are not supported because file() and fileset() are evaluated at plan time."
  type        = string
}

variable "repository_partitions" {
  description = "List of partition names (subdirectories under config/repository/) to load. An empty list loads all partitions. Top-level *.yml files in config/repository/ are always loaded regardless of this setting."
  type        = list(string)
  default     = []
}

variable "webhook_secrets" {
  description = "Map of webhook secret names to their values. Keys should match the VAR_NAME in env:VAR_NAME patterns used in webhook configurations."
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "membership_management_enabled" {
  description = <<-EOT
    Enable organization membership management via YAML configuration in config/membership/.

    **Safety warning:** Defaults to false. When enabled, removing a username from config/membership/
    will remove that person from the GitHub organization on the next `terraform apply`, which
    revokes access to all private repositories and destroys private forks. Always run
    `terraform plan` and review the output carefully before applying.

    **SCIM/SSO conflict:** Do NOT enable this if your organization uses SCIM or an IdP for
    membership provisioning (e.g., Okta, Azure AD, GitHub Enterprise SCIM). Terraform and SCIM
    will conflict and cause unexpected membership changes.

    Only effective when the target account is an organization (is_organization: true in config.yml).
    Has no effect on personal accounts.
  EOT
  type        = bool
  default     = false
}
