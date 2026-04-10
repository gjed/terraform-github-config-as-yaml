variable "name" {
  description = "Repository name"
  type        = string
}

variable "description" {
  description = "Repository description"
  type        = string
}

variable "visibility" {
  description = "Repository visibility (public, private, or internal)"
  type        = string
  default     = "private"

  validation {
    condition     = contains(["public", "private", "internal"], var.visibility)
    error_message = "Visibility must be public, private, or internal."
  }
}

variable "has_wiki" {
  description = "Enable repository wiki"
  type        = bool
  default     = false
}

variable "has_issues" {
  description = "Enable repository issues"
  type        = bool
  default     = false
}

variable "has_projects" {
  description = "Enable repository projects"
  type        = bool
  default     = false
}

variable "has_discussions" {
  description = "Enable repository discussions"
  type        = bool
  default     = false
}

variable "allow_merge_commit" {
  description = "Allow merge commits"
  type        = bool
  default     = true
}

variable "allow_squash_merge" {
  description = "Allow squash merges"
  type        = bool
  default     = true
}

variable "allow_rebase_merge" {
  description = "Allow rebase merges"
  type        = bool
  default     = true
}

variable "delete_branch_on_merge" {
  description = "Automatically delete head branch after merging"
  type        = bool
  default     = false
}

variable "allow_auto_merge" {
  description = "Allow auto-merge on pull requests"
  type        = bool
  default     = false
}

variable "allow_update_branch" {
  description = "Always suggest updating pull request branches"
  type        = bool
  default     = false
}

variable "web_commit_signoff_required" {
  description = "Require contributors to sign off on web-based commits"
  type        = bool
  default     = false
}

variable "vulnerability_alerts" {
  description = "Enable security alerts for vulnerable dependencies"
  type        = bool
  default     = true
}

variable "topics" {
  description = "Repository topics"
  type        = list(string)
  default     = []
}

variable "auto_init" {
  description = "Initialize repository with README"
  type        = bool
  default     = false
}

variable "gitignore_template" {
  description = "Gitignore template to use"
  type        = string
  default     = null
}

variable "license_template" {
  description = "License template to use"
  type        = string
  default     = null
}

variable "homepage_url" {
  description = "URL of a page describing the project"
  type        = string
  default     = null
}

variable "teams" {
  description = "Map of team slugs to their permission level (pull, triage, push, maintain, admin)"
  type        = map(string)
  default     = {}
}

variable "collaborators" {
  description = "Map of GitHub usernames to their permission level (pull, triage, push, maintain, admin)"
  type        = map(string)
  default     = {}
}

variable "rulesets" {
  description = "Map of repository rulesets to apply"
  type = map(object({
    target      = string
    enforcement = string
    conditions = object({
      ref_name = object({
        include = list(string)
        exclude = list(string)
      })
    })
    rules = list(object({
      type    = string
      enabled = optional(bool, true)
      parameters = optional(object({
        required_approving_review_count   = optional(number)
        dismiss_stale_reviews_on_push     = optional(bool)
        require_code_owner_review         = optional(bool)
        require_last_push_approval        = optional(bool)
        required_review_thread_resolution = optional(bool)
        required_checks = optional(list(object({
          context        = string
          integration_id = optional(number)
        })))
        strict_required_status_checks_policy = optional(bool)
        update_allows_fetch_and_merge        = optional(bool)
        required_deployment_environments     = optional(list(string))
        operator                             = optional(string)
        pattern                              = optional(string)
        name                                 = optional(string)
        negate                               = optional(bool)
      }))
    }))
    bypass_actors = optional(list(object({
      actor_id    = number
      actor_type  = string
      bypass_mode = optional(string)
    })))
  }))
  default = {}
}

variable "actions" {
  description = "GitHub Actions permissions configuration for the repository"
  type = object({
    # Enable/disable Actions for this repository
    enabled = optional(bool, true)

    # Which actions are allowed to run: all, local_only, selected
    allowed_actions = optional(string, "all")

    # Configuration when allowed_actions is "selected"
    allowed_actions_config = optional(object({
      github_owned_allowed = optional(bool, true)
      verified_allowed     = optional(bool, true)
      patterns_allowed     = optional(list(string), [])
    }))
  })
  default = null

  validation {
    condition     = var.actions == null || contains(["all", "local_only", "selected"], coalesce(var.actions.allowed_actions, "all"))
    error_message = "allowed_actions must be 'all', 'local_only', or 'selected'."
  }
}
variable "webhooks" {
  description = "Map of repository webhooks to create"
  type = map(object({
    url          = string
    content_type = optional(string, "json")
    secret       = optional(string)
    events       = list(string)
    active       = optional(bool, true)
    insecure_ssl = optional(bool, false)
  }))
  default = {}
}

variable "branch_protections" {
  description = "Map of branch protection rules to apply"
  type = map(object({
    pattern                         = string
    enforce_admins                  = optional(bool, false)
    allows_deletions                = optional(bool, false)
    allows_force_pushes             = optional(bool, false)
    lock_branch                     = optional(bool, false)
    require_conversation_resolution = optional(bool, false)
    require_signed_commits          = optional(bool, false)
    required_linear_history         = optional(bool, false)

    required_pull_request_reviews = optional(object({
      required_approving_review_count = optional(number, 1)
      dismiss_stale_reviews           = optional(bool, false)
      require_code_owner_reviews      = optional(bool, false)
      require_last_push_approval      = optional(bool, false)
      restrict_dismissals             = optional(bool, false)
      dismissal_restrictions = optional(object({
        users = optional(list(string), [])
        teams = optional(list(string), [])
        apps  = optional(list(string), [])
      }))
      pull_request_bypassers = optional(object({
        users = optional(list(string), [])
        teams = optional(list(string), [])
        apps  = optional(list(string), [])
      }))
    }))

    required_status_checks = optional(object({
      strict   = optional(bool, false)
      contexts = optional(list(string), [])
    }))

    restrict_pushes = optional(object({
      blocks_creations = optional(bool, true)
      push_allowances = optional(object({
        users = optional(list(string), [])
        teams = optional(list(string), [])
        apps  = optional(list(string), [])
      }))
    }))
  }))
  default = {}
}
