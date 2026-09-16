# Variables for the GitHub org Terraform module

variable "config_path" {
  description = "Absolute path to the directory containing config.yml, group/, repository/, ruleset/, and webhook/ subdirectories. Consumers should set this to path.root + \"/config\". Must be a static string - computed values are not supported because file() and fileset() are evaluated at plan time."
  type        = string
}

variable "repository_partitions" {
  description = <<-EOT
    List of partition names (subdirectories under config/repository/) to load.
    Type and default are unchanged: list(string), default [].

    **Empty list (default):** Loads all partitions and all top-level *.yml files in config/repository/.
    This is the normal mode for single-state consumers and carries zero destroy risk.

    **Non-empty list:** Selects specific partitions. This is a STATIC STATE-SHARDING mechanism only:
    each non-empty value MUST be paired with a dedicated Terraform state (its own root module and
    backend), set once at bootstrap and never varied between plans against that same state.

    **CRITICAL — Never narrow against a shared state:** Changing repository_partitions from [] to
    a subset in a Terraform state that has ever managed repositories outside the new selection
    causes Terraform to plan their destruction. Terraform has no mechanism to leave an orphaned
    for_each instance untouched: it is either present in the desired config (refreshed) or absent
    (destroyed). Narrowing against a shared state is unsupported and will destroy every repository
    outside the new selection.

    For safe alternatives that work on a single state with zero destroy risk, see docs/scaling.md
    section "Reducing plan cost with -refresh=false" and the module's partition-detection script.
  EOT
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
