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
    enabled      = optional(bool, true)
    algorithm    = optional(string, "round_robin")
    member_count = optional(number, 1)
    notify       = optional(bool, true)
  })
  default = null

  # The provider only accepts ROUND_ROBIN and LOAD_BALANCE and rejects anything
  # else outright ("expected algorithm to be one of [ROUND_ROBIN LOAD_BALANCE]").
  # Both casings are accepted here and normalised in main.tf, so configurations
  # written against the previous lowercase documentation keep working.
  validation {
    condition     = var.review_request_delegation == null || contains(["ROUND_ROBIN", "LOAD_BALANCE"], upper(coalesce(var.review_request_delegation.algorithm, "ROUND_ROBIN")))
    error_message = "Algorithm must be 'ROUND_ROBIN' or 'LOAD_BALANCE' (case-insensitive)."
  }

  validation {
    condition     = var.review_request_delegation == null || coalesce(var.review_request_delegation.member_count, 1) > 0
    error_message = "member_count must be greater than 0."
  }
}
