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
    enabled      = bool
    algorithm    = optional(string, "round_robin")
    member_count = optional(number, 1)
    notify       = optional(bool, true)
  })
  default = null

  validation {
    condition     = var.review_request_delegation == null || contains(["round_robin", "load_balance"], coalesce(var.review_request_delegation.algorithm, "round_robin"))
    error_message = "Algorithm must be 'round_robin' or 'load_balance'."
  }
}
