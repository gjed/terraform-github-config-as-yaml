# Load and parse YAML configuration
locals {
  # Configuration directory paths
  config_base_path       = var.config_path
  repository_config_path = "${local.config_base_path}/repository"
  group_config_path      = "${local.config_base_path}/group"
  ruleset_config_path    = "${local.config_base_path}/ruleset"
  membership_config_path = "${local.config_base_path}/membership"

  # Read common config (single file - not splittable)
  common_config = yamldecode(file("${local.config_base_path}/config.yml"))

  # Discover partition subdirectories under config/repository/
  # Each immediate subdirectory is a named partition
  repository_partition_dirs = toset([
    for f in fileset(local.repository_config_path, "*/*.yml") :
    split("/", f)[0]
  ])

  # Resolve active partitions: empty list means all discovered partitions
  active_partitions = length(var.repository_partitions) == 0 ? local.repository_partition_dirs : toset(var.repository_partitions)

  # Partition-aware repository file collection:
  # - Top-level *.yml files are always loaded (no path prefix)
  # - Active partition files are loaded with "<partition>/" prefix so file paths are unique
  repository_files = toset(concat(
    tolist(fileset(local.repository_config_path, "*.yml")),
    flatten([
      for partition in setintersection(local.active_partitions, local.repository_partition_dirs) :
      [for f in fileset("${local.repository_config_path}/${partition}", "*.yml") : "${partition}/${f}"]
    ])
  ))

  group_files   = fileset(local.group_config_path, "*.yml")
  ruleset_files = fileset(local.ruleset_config_path, "*.yml")

  # Membership directory is optional - missing directory results in empty set
  membership_files = try(
    fileset(local.membership_config_path, "*.yml"),
    toset([])
  )

  # Load individual YAML files (for duplicate detection)
  repository_configs_by_file = {
    for f in sort(tolist(local.repository_files)) :
    f => yamldecode(file("${local.repository_config_path}/${f}"))
  }
  group_configs_by_file = {
    for f in sort(tolist(local.group_files)) :
    f => yamldecode(file("${local.group_config_path}/${f}"))
  }
  ruleset_configs_by_file = {
    for f in sort(tolist(local.ruleset_files)) :
    f => yamldecode(file("${local.ruleset_config_path}/${f}"))
  }
  membership_configs_by_file = {
    for f in sort(tolist(local.membership_files)) :
    f => yamldecode(file("${local.membership_config_path}/${f}"))
  }

  # Detect duplicate keys across files
  # Build a map of key -> list of files for each config type
  repo_key_occurrences = {
    for key in distinct(flatten([
      for file, config in local.repository_configs_by_file :
      config != null ? keys(config) : []
    ])) :
    key => [
      for file, config in local.repository_configs_by_file :
      file if config != null && contains(keys(config), key)
    ]
  }

  group_key_occurrences = {
    for key in distinct(flatten([
      for file, config in local.group_configs_by_file :
      config != null ? keys(config) : []
    ])) :
    key => [
      for file, config in local.group_configs_by_file :
      file if config != null && contains(keys(config), key)
    ]
  }

  ruleset_key_occurrences = {
    for key in distinct(flatten([
      for file, config in local.ruleset_configs_by_file :
      config != null ? keys(config) : []
    ])) :
    key => [
      for file, config in local.ruleset_configs_by_file :
      file if config != null && contains(keys(config), key)
    ]
  }

  # Validate requested partition names against discovered directories
  invalid_partition_names = [
    for p in var.repository_partitions :
    p if !contains(tolist(local.repository_partition_dirs), p)
  ]

  # Filter to only duplicates (appearing in more than one file)
  duplicate_repository_keys = {
    for key, files in local.repo_key_occurrences :
    key => files if length(files) > 1
  }

  duplicate_group_keys = {
    for key, files in local.group_key_occurrences :
    key => files if length(files) > 1
  }

  duplicate_ruleset_keys = {
    for key, files in local.ruleset_key_occurrences :
    key => files if length(files) > 1
  }

  membership_key_occurrences = {
    for key in distinct(flatten([
      for file, config in local.membership_configs_by_file :
      config != null ? keys(config) : []
    ])) :
    key => [
      for file, config in local.membership_configs_by_file :
      file if config != null && contains(keys(config), key)
    ]
  }

  duplicate_membership_keys = {
    for key, files in local.membership_key_occurrences :
    key => files if length(files) > 1
  }

  # Load and merge repository configs from config/repository/ directory
  repos_config = merge([
    for f in sort(tolist(local.repository_files)) :
    yamldecode(file("${local.repository_config_path}/${f}"))
  ]...)

  # Load and merge group configs from config/group/ directory
  groups_config = merge([
    for f in sort(tolist(local.group_files)) :
    yamldecode(file("${local.group_config_path}/${f}"))
  ]...)

  # Load and merge ruleset configs from config/ruleset/ directory
  # Note: templates.yml is loaded separately and not merged with rulesets_config
  rulesets_config = merge([
    for f in sort(tolist(local.ruleset_files)) :
    yamldecode(file("${local.ruleset_config_path}/${f}"))
    if f != "templates.yml" # Exclude templates from regular rulesets
  ]...)

  # Separate rulesets by scope
  # - repo_rulesets_config: definitions without 'scope' or with 'scope: repository'
  #   These are available for assignment via rulesets: in groups and repositories
  # - org_rulesets_config: definitions with 'scope: organization'
  #   These are applied as github_organization_ruleset resources, not per-repository
  repo_rulesets_config = {
    for name, config in local.rulesets_config :
    name => config
    if lookup(config, "scope", "repository") != "organization"
  }

  org_rulesets_config = {
    for name, config in local.rulesets_config :
    name => config
    if lookup(config, "scope", "repository") == "organization"
  }

  # Load ruleset templates from config/ruleset/default-rulesets.yml
  # Templates are referenced by name in repository/group configurations
  # This file now contains both templates and default rulesets
  ruleset_templates = try(
    yamldecode(file("${local.ruleset_config_path}/default-rulesets.yml")),
    {}
  )

  # Load webhook definitions from config/webhook/ directory
  # Directory is optional - missing directory results in empty map
  webhook_dir = "${local.config_base_path}/webhook"
  webhook_files = try(
    fileset(local.webhook_dir, "*.yml"),
    toset([])
  )
  webhooks_config = merge([
    for f in sort(tolist(local.webhook_files)) :
    try(yamldecode(file("${local.webhook_dir}/${f}")), {})
  ]...)

  # Load team definitions from config/team/ directory
  # Directory is optional - missing directory results in empty map
  team_dir = "${local.config_base_path}/team"
  team_files = try(
    fileset(local.team_dir, "*.yml"),
    toset([])
  )
  # Load per-file for duplicate-slug detection (mirrors repo/group/ruleset pattern)
  team_configs_by_file = {
    for f in sort(tolist(local.team_files)) :
    f => try(yamldecode(file("${local.team_dir}/${f}")), {})
  }
  duplicate_team_slugs = {
    for slug in distinct(flatten([
      for f, config in local.team_configs_by_file :
      config != null ? keys(config) : []
    ])) :
    slug => [
      for f, config in local.team_configs_by_file :
      f if config != null && contains(keys(config), slug)
    ]
    if length([
      for f, config in local.team_configs_by_file :
      f if config != null && contains(keys(config), slug)
    ]) > 1
  }
  teams_config_raw = merge([
    for f in sort(tolist(local.team_files)) :
    try(yamldecode(file("${local.team_dir}/${f}")), {})
  ]...)

  # Flatten nested team hierarchy into a tiered flat map
  # Input: nested YAML where child teams are under parent's `teams` key
  # Output: flat map of slug => { description, privacy, members, maintainers,
  #          review_request_delegation, parent_slug, tier }
  #
  # Tier 0: root teams (no parent)
  # Tier 1: children of tier 0
  # Tier 2: children of tier 1 (max depth)
  #
  # All optional list/map fields use coalesce(lookup(..., null), fallback) so that
  # an explicit `key: null` in YAML is treated the same as an absent key.

  # Tier 0 - root level teams
  tier_0_teams = {
    for slug, config in local.teams_config_raw : slug => {
      name                      = slug
      description               = config.description
      privacy                   = coalesce(lookup(config, "privacy", null), "closed")
      members                   = coalesce(lookup(config, "members", null), [])
      maintainers               = coalesce(lookup(config, "maintainers", null), [])
      review_request_delegation = lookup(config, "review_request_delegation", null)
      parent_slug               = null
      tier                      = 0
    }
  }

  # Tier 1 - children of root teams
  tier_1_teams = merge([
    for parent_slug, parent_config in local.teams_config_raw : {
      for child_slug, child_config in coalesce(lookup(parent_config, "teams", null), {}) : child_slug => {
        name                      = child_slug
        description               = child_config.description
        privacy                   = coalesce(lookup(child_config, "privacy", null), "closed")
        members                   = coalesce(lookup(child_config, "members", null), [])
        maintainers               = coalesce(lookup(child_config, "maintainers", null), [])
        review_request_delegation = lookup(child_config, "review_request_delegation", null)
        parent_slug               = parent_slug
        tier                      = 1
      }
    }
  ]...)

  # Tier 2 - grandchildren (children of tier 1)
  tier_2_teams = merge([
    for parent_slug, parent_config in local.teams_config_raw : merge([
      for child_slug, child_config in coalesce(lookup(parent_config, "teams", null), {}) : {
        for grandchild_slug, grandchild_config in coalesce(lookup(child_config, "teams", null), {}) : grandchild_slug => {
          name                      = grandchild_slug
          description               = grandchild_config.description
          privacy                   = coalesce(lookup(grandchild_config, "privacy", null), "closed")
          members                   = coalesce(lookup(grandchild_config, "members", null), [])
          maintainers               = coalesce(lookup(grandchild_config, "maintainers", null), [])
          review_request_delegation = lookup(grandchild_config, "review_request_delegation", null)
          parent_slug               = child_slug
          tier                      = 2
        }
      }
    ]...)
  ]...)

  # Combined flat map of all teams (for validation and outputs)
  all_teams = merge(local.tier_0_teams, local.tier_1_teams, local.tier_2_teams)

  # Raw child counts BEFORE merge - used to detect intra-tier duplicate slugs.
  # merge([...]) silently drops entries when two parents share a child slug, so
  # length(tier_N_teams) < tier_N_raw_count means a collision occurred.
  tier_1_raw_count = length(flatten([
    for parent_slug, parent_config in local.teams_config_raw :
    keys(coalesce(lookup(parent_config, "teams", null), {}))
  ]))
  tier_2_raw_count = length(flatten([
    for parent_slug, parent_config in local.teams_config_raw : flatten([
      for child_slug, child_config in coalesce(lookup(parent_config, "teams", null), {}) :
      keys(coalesce(lookup(child_config, "teams", null), {}))
    ])
  ]))

  # Load and merge membership configs from config/membership/ directory (optional).
  # Derived from membership_configs_by_file to avoid re-reading files.
  # Null entries (comment-only files) are excluded explicitly rather than via try(),
  # so that genuinely invalid YAML still fails loudly at plan time.
  membership_config = merge([
    for f, config in local.membership_configs_by_file :
    config != null ? config : {}
  ]...)

  # Load branch protection definitions from config/branch-protection/ directory
  # Directory is optional - missing directory results in empty map (no error)
  branch_protection_config_path = "${local.config_base_path}/branch-protection"
  branch_protection_files = try(
    fileset(local.branch_protection_config_path, "*.yml"),
    toset([])
  )

  # Load individual YAML files (for duplicate detection)
  branch_protection_configs_by_file = {
    for f in sort(tolist(local.branch_protection_files)) :
    f => yamldecode(file("${local.branch_protection_config_path}/${f}"))
  }

  # Detect duplicate branch protection keys across files
  branch_protection_key_occurrences = {
    for key in distinct(flatten([
      for file, config in local.branch_protection_configs_by_file :
      config != null ? keys(config) : []
    ])) :
    key => [
      for file, config in local.branch_protection_configs_by_file :
      file if config != null && contains(keys(config), key)
    ]
  }

  duplicate_branch_protection_keys = {
    for key, files in local.branch_protection_key_occurrences :
    key => files if length(files) > 1
  }

  # Merge all branch protection definitions into a single map (alphabetical file order)
  # Seeded with {} so merge() is never called with zero arguments when the directory is empty
  branch_protections_config = merge({}, [
    for f in sort(tolist(local.branch_protection_files)) :
    yamldecode(file("${local.branch_protection_config_path}/${f}"))
  ]...)

  # Extract values from YAML
  github_org      = local.common_config.organization
  is_organization = lookup(local.common_config, "is_organization", true)
  subscription    = lookup(local.common_config, "subscription", "free")
  config_groups   = local.groups_config
  repos_yaml      = local.repos_config

  # Organization-level actions configuration
  # Defaults to null if not specified (no org-level actions resource created)
  # Only applicable for organizations, not personal accounts
  org_actions_config = local.is_organization ? lookup(local.common_config, "actions", null) : null

  # Effective membership: only managed when explicitly enabled AND target is an organization
  # Returns empty map when membership_management_enabled is false OR is_organization is false
  effective_membership = (
    var.membership_management_enabled && local.is_organization
  ) ? local.membership_config : {}
  # Organization-level webhook names
  # Reads the org_webhooks list from config.yml; empty for personal accounts
  org_webhook_names = local.is_organization ? tolist(lookup(local.common_config, "org_webhooks", [])) : []

  # Organization webhook invalid references (for check block)
  # Collects any org_webhook names not defined in config/webhook/
  invalid_org_webhook_refs = [
    for name in local.org_webhook_names : name
    if lookup(local.webhooks_config, name, null) == null
  ]

  # Resolve org webhook definitions: look up each name in webhooks_config,
  # normalize types, and apply env:VAR_NAME secret resolution.
  # Only populated for organizations; empty map for personal accounts.
  resolved_org_webhooks_raw = local.is_organization ? {
    for name in local.org_webhook_names : name => {
      url          = tostring(lookup(local.webhooks_config, name, { url = null }).url)
      content_type = tostring(lookup(lookup(local.webhooks_config, name, {}), "content_type", "json"))
      secret       = try(tostring(lookup(local.webhooks_config, name, {}).secret), null)
      events       = tolist(lookup(lookup(local.webhooks_config, name, {}), "events", []))
      active       = tobool(lookup(lookup(local.webhooks_config, name, {}), "active", true))
      insecure_ssl = tobool(lookup(lookup(local.webhooks_config, name, {}), "insecure_ssl", false))
    }
    if lookup(local.webhooks_config, name, null) != null
  } : {}

  # Resolve env:VAR_NAME secrets for org webhooks (same pattern as repo webhooks)
  resolved_org_webhooks = {
    for name, webhook in local.resolved_org_webhooks_raw : name => {
      url          = webhook.url
      content_type = webhook.content_type
      secret = (
        webhook.secret != null && can(regex("^env:", webhook.secret)) ?
        lookup(var.webhook_secrets, substr(webhook.secret, 4, -1), null) :
        webhook.secret
      )
      events       = webhook.events
      active       = webhook.active
      insecure_ssl = webhook.insecure_ssl
    }
  }

  # 1.1 Organization-level settings configuration
  # Parses optional `settings:` block from config.yml.
  # Returns null when: is_organization=false, block absent, or value is not a map.
  # The try() guard prevents hard errors when `settings:` is accidentally set to a scalar.
  org_settings_raw = local.is_organization ? (
    lookup(local.common_config, "settings", null) != null ? try(
      { for k, v in local.common_config.settings : k => v },
      null
    ) : null
  ) : null

  # 1.3 GHAS (GitHub Advanced Security) features require Enterprise subscription
  ghas_settings_enabled = local.subscription == "enterprise"

  # Keys that require GitHub Enterprise subscription
  # These are silently removed from effective settings on non-enterprise tiers
  enterprise_only_keys = [
    "advanced_security_enabled_for_new_repositories",
    "secret_scanning_enabled_for_new_repositories",
    "secret_scanning_push_protection_enabled_for_new_repositories",
    "members_can_create_internal_repositories",
  ]

  # 1.5 Collect skipped enterprise-only keys for warnings output
  org_settings_warnings = (
    local.org_settings_raw != null && !local.ghas_settings_enabled
    ) ? [
    for key in local.enterprise_only_keys :
    key if contains(keys(local.org_settings_raw), key)
  ] : []

  # 1.4 Apply enterprise-key filtering to the raw map
  org_settings_effective = local.org_settings_raw != null ? (
    local.ghas_settings_enabled ? local.org_settings_raw : {
      for k, v in local.org_settings_raw : k => v
      if !contains(local.enterprise_only_keys, k)
    }
  ) : null

  # 1.2 Final effective config used to gate resource creation.
  # Null when:
  #   - raw is null (is_organization=false, settings absent, or not a map)
  #   - filtering left an empty map (only enterprise-only keys set on non-enterprise tier)
  #   - billing_email is absent (required by provider; validation script enforces this)
  org_settings_config = (
    local.org_settings_effective != null &&
    length(local.org_settings_effective) > 0 &&
    contains(keys(local.org_settings_effective), "billing_email")
  ) ? local.org_settings_effective : null

  # Subscription tier feature availability
  # - free: Rulesets only work on public repositories
  # - pro: Rulesets work on public and private repositories
  # - team/enterprise: Full ruleset support including push rulesets
  rulesets_require_paid_for_private = contains(["free"], local.subscription)

  # Organization rulesets require organization mode and team/enterprise subscription
  # On free or pro plans, or when not in organization mode, all org rulesets are skipped
  org_rulesets_require_paid = local.is_organization && contains(["free", "pro"], local.subscription)

  # Effective org rulesets after account type and subscription tier filtering
  # Returns empty map when not in organization mode or when subscription is insufficient
  effective_org_rulesets = local.is_organization && !local.org_rulesets_require_paid ? local.org_rulesets_config : tomap({})

  # Track which org rulesets are skipped due to subscription tier
  # (only meaningful in organization mode; personal accounts simply never have org rulesets)
  skipped_org_ruleset_names = local.is_organization && local.org_rulesets_require_paid ? keys(local.org_rulesets_config) : []

  # Merge multiple config groups for each repository
  # Groups are applied sequentially: later groups override single values, lists are merged
  merged_configs = {
    for repo_name, repo_config in local.repos_yaml : repo_name => merge(
      # Apply each group sequentially - merge will override with later values
      [
        for group_name in repo_config.groups :
        lookup(local.config_groups, group_name, {})
      ]...
    )
  }

  # Merge topics from all groups for each repository
  merged_topics = {
    for repo_name, repo_config in local.repos_yaml : repo_name => distinct(flatten([
      # Topics from all groups
      for group_name in repo_config.groups :
      lookup(lookup(local.config_groups, group_name, {}), "topics", [])
    ]))
  }

  # Merge teams from all groups for each repository
  merged_teams = {
    for repo_name, repo_config in local.repos_yaml : repo_name => merge(
      # Apply each group's teams sequentially - later groups override
      [
        for group_name in repo_config.groups :
        lookup(lookup(local.config_groups, group_name, {}), "teams", {})
      ]...
    )
  }

  # Merge collaborators from all groups for each repository
  merged_collaborators = {
    for repo_name, repo_config in local.repos_yaml : repo_name => merge(
      # Apply each group's collaborators sequentially - later groups override
      [
        for group_name in repo_config.groups :
        lookup(lookup(local.config_groups, group_name, {}), "collaborators", {})
      ]...
    )
  }

  # Merge rulesets from all groups for each repository
  # Rulesets are collected from groups, then repo-specific rulesets are added
  # Supports both direct ruleset names and template references with overrides
  # Note: On free tier, rulesets are skipped for private repositories
  merged_rulesets = {
    for repo_name, repo_config in local.repos_yaml : repo_name => merge([
      for idx, ruleset_entry in flatten(concat(
        # Collect ruleset entries from all groups
        [
          for group_name in repo_config.groups :
          lookup(lookup(local.config_groups, group_name, {}), "rulesets", [])
        ],
        # Add repo-specific rulesets
        [lookup(repo_config, "rulesets", [])]
        )) : {
        # Generate a unique key for this ruleset
        # For templates, use "tpl-<template_name>-<idx>" to avoid collisions
        # For direct references, use the ruleset name as-is
        (try(ruleset_entry.template, null) != null ?
          "tpl-${ruleset_entry.template}-${idx}" :
          tostring(ruleset_entry)
          ) = (
          # If entry is a map with 'template' key, resolve from templates
          try(ruleset_entry.template, null) != null ? (
            # Validate template exists
            lookup(local.ruleset_templates, ruleset_entry.template, null) != null ? (
              # Merge template base with any inline overrides
              merge(
                local.ruleset_templates[ruleset_entry.template],
                # Exclude 'template' key from overrides
                {
                  for k, v in ruleset_entry : k => v
                  if k != "template"
                }
              )
            ) : null # Template doesn't exist - will be filtered out
            ) : (
            # Direct ruleset name reference (existing behavior)
            # Only looks up repo-scoped rulesets; org-scoped rulesets are excluded here
            lookup(local.repo_rulesets_config, ruleset_entry, null)
          )
        )
      }
    ]...)
  }

  # Merge actions configuration from all groups for each repository
  # Actions config uses deep merge: scalar values override, lists are merged
  # Secure defaults: allowed_actions defaults to "all" to match GitHub's default
  # Merge actions patterns_allowed from all groups + repo-specific patterns
  # Lists are merged (deduplicated) rather than overridden
  merged_actions_patterns = {
    for repo_name, repo_config in local.repos_yaml : repo_name => distinct(flatten(concat(
      # Collect patterns from all groups
      [
        for group_name in repo_config.groups :
        lookup(
          lookup(
            lookup(local.config_groups, group_name, {}),
            "actions",
            {}
          ),
          "allowed_actions_config",
          {}
          ) != {} ? lookup(
          lookup(
            lookup(local.config_groups, group_name, {}),
            "actions",
            {}
          ),
          "allowed_actions_config",
          null
          ) != null ? lookup(
          lookup(
            lookup(
              lookup(local.config_groups, group_name, {}),
              "actions",
              {}
            ),
            "allowed_actions_config",
            {}
          ),
          "patterns_allowed",
          []
        ) : [] : []
      ],
      # Add repo-specific patterns
      lookup(repo_config, "actions", null) != null && lookup(lookup(repo_config, "actions", {}), "allowed_actions_config", null) != null ? [
        lookup(
          lookup(
            lookup(repo_config, "actions", {}),
            "allowed_actions_config",
            {}
          ),
          "patterns_allowed",
          []
        )
      ] : []
    )))
  }

  # Determine effective actions config for each repository
  # This merges group configs with repo-specific overrides and applies secure defaults
  effective_actions = {
    for repo_name, repo_config in local.repos_yaml : repo_name => (
      # Check if ANY actions config exists in groups or repo
      lookup(repo_config, "actions", null) != null ||
      anytrue([
        for group_name in repo_config.groups :
        lookup(lookup(local.config_groups, group_name, {}), "actions", null) != null
      ])
      ) ? {
      # Enabled: repo > groups > true (secure default allows actions)
      enabled = coalesce(
        lookup(repo_config, "actions", null) != null ? lookup(lookup(repo_config, "actions", {}), "enabled", null) : null,
        # Check groups in reverse order (last group wins)
        try([
          for group_name in reverse(repo_config.groups) :
          lookup(
            lookup(
              lookup(local.config_groups, group_name, {}),
              "actions",
              {}
            ),
            "enabled",
            null
          )
          if lookup(
            lookup(
              lookup(local.config_groups, group_name, {}),
              "actions",
              {}
            ),
            "enabled",
            null
          ) != null
        ][0], null),
        true
      )

      # Allowed actions: repo > groups > "all" (GitHub's default)
      allowed_actions = coalesce(
        lookup(repo_config, "actions", null) != null ? lookup(lookup(repo_config, "actions", {}), "allowed_actions", null) : null,
        try([
          for group_name in reverse(repo_config.groups) :
          lookup(
            lookup(
              lookup(local.config_groups, group_name, {}),
              "actions",
              {}
            ),
            "allowed_actions",
            null
          )
          if lookup(
            lookup(
              lookup(local.config_groups, group_name, {}),
              "actions",
              {}
            ),
            "allowed_actions",
            null
          ) != null
        ][0], null),
        "all"
      )

      # Allowed actions config: only included when allowed_actions is "selected"
      allowed_actions_config = {
        github_owned_allowed = coalesce(
          lookup(repo_config, "actions", null) != null &&
          lookup(lookup(repo_config, "actions", {}), "allowed_actions_config", null) != null
          ? lookup(
            lookup(lookup(repo_config, "actions", {}), "allowed_actions_config", {}),
            "github_owned_allowed",
            null
          ) : null,
          try([
            for group_name in reverse(repo_config.groups) :
            lookup(
              lookup(
                lookup(
                  lookup(local.config_groups, group_name, {}),
                  "actions",
                  {}
                ),
                "allowed_actions_config",
                {}
              ),
              "github_owned_allowed",
              null
            )
            if lookup(
              lookup(
                lookup(
                  lookup(local.config_groups, group_name, {}),
                  "actions",
                  {}
                ),
                "allowed_actions_config",
                {}
              ),
              "github_owned_allowed",
              null
            ) != null
          ][0], null),
          true # Secure default: allow github-owned actions
        )

        verified_allowed = coalesce(
          lookup(repo_config, "actions", null) != null &&
          lookup(lookup(repo_config, "actions", {}), "allowed_actions_config", null) != null
          ? lookup(
            lookup(lookup(repo_config, "actions", {}), "allowed_actions_config", {}),
            "verified_allowed",
            null
          ) : null,
          try([
            for group_name in reverse(repo_config.groups) :
            lookup(
              lookup(
                lookup(
                  lookup(local.config_groups, group_name, {}),
                  "actions",
                  {}
                ),
                "allowed_actions_config",
                {}
              ),
              "verified_allowed",
              null
            )
            if lookup(
              lookup(
                lookup(
                  lookup(local.config_groups, group_name, {}),
                  "actions",
                  {}
                ),
                "allowed_actions_config",
                {}
              ),
              "verified_allowed",
              null
            ) != null
          ][0], null),
          true # Secure default: allow verified marketplace actions
        )

        # Patterns are merged from all groups + repo
        patterns_allowed = local.merged_actions_patterns[repo_name]
      }
    } : null
  }
  # Merge branch protections from all groups for each repository
  # Collected from groups in order, repo-specific appended, deduplicated by name (last wins)
  # No subscription tier filtering - branch protection works on all tiers including free-tier private repos
  merged_branch_protections = {
    for repo_name, repo_config in local.repos_yaml : repo_name => merge({}, [
      for entry in flatten(concat(
        # Collect branch protection names from all groups (in order)
        [
          for group_name in repo_config.groups :
          lookup(lookup(local.config_groups, group_name, {}), "branch_protections", [])
        ],
        # Append repo-specific branch protections
        [lookup(repo_config, "branch_protections", [])]
        )) : {
        (entry) = lookup(local.branch_protections_config, entry, null)
      }
      if lookup(local.branch_protections_config, entry, null) != null
    ]...)
  }

  # Validate that all template references exist
  # Collects any invalid template references across all repos and groups
  # Note: ruleset_entry can be either a string (direct reference) or an object (template reference)
  invalid_template_refs = flatten([
    for repo_name, repo_config in local.repos_yaml : [
      for ruleset_entry in flatten(concat(
        [
          for group_name in repo_config.groups :
          lookup(lookup(local.config_groups, group_name, {}), "rulesets", [])
        ],
        [lookup(repo_config, "rulesets", [])]
        )) : {
        repo     = repo_name
        template = ruleset_entry.template
      }
      # Only validate if it's an object with a template key (not a direct string reference)
      if can(ruleset_entry.template) && try(ruleset_entry.template, null) != null && lookup(local.ruleset_templates, ruleset_entry.template, null) == null
    ]
  ])

  # Collect invalid branch protection references (referenced names not in branch_protections_config)
  invalid_branch_protection_refs = flatten([
    for repo_name, repo_config in local.repos_yaml : [
      for entry in flatten(concat(
        [
          for group_name in repo_config.groups :
          lookup(lookup(local.config_groups, group_name, {}), "branch_protections", [])
        ],
        [lookup(repo_config, "branch_protections", [])]
        )) : {
        repo  = repo_name
        entry = entry
      }
      if lookup(local.branch_protections_config, entry, null) == null && entry != null
    ]
  ])

  # Calculate effective visibility for each repository (needed for ruleset filtering)
  repo_visibility = {
    for repo_name, repo_config in local.repos_yaml : repo_name =>
    lookup(repo_config, "visibility", lookup(local.merged_configs[repo_name], "visibility", "private"))
  }

  # Filter rulesets based on subscription tier and repository visibility
  # On free tier, rulesets are not available for private repositories
  effective_rulesets = {
    for repo_name, rulesets in local.merged_rulesets : repo_name =>
    (local.rulesets_require_paid_for_private && local.repo_visibility[repo_name] != "public") ? tomap({}) : rulesets
  }

  # Track which repos have rulesets skipped due to subscription limitations
  repos_with_skipped_rulesets = [
    for repo_name, rulesets in local.merged_rulesets : repo_name
    if length(rulesets) > 0 && length(local.effective_rulesets[repo_name]) == 0
  ]

  # Merge webhooks from groups and repo for each repository
  # Later definitions override earlier ones by name (groups applied in order, then repo overrides)
  merged_webhooks_raw = {
    for repo_name, repo_config in local.repos_yaml : repo_name => merge(
      concat(
        # Apply each group's webhooks sequentially - later groups override by name
        [
          for group_name in repo_config.groups : {
            for entry in lookup(lookup(local.config_groups, group_name, {}), "webhooks", []) :
            (can(tostring(entry)) ? tostring(entry) : lookup(entry, "name", "")) => (
              can(tostring(entry)) ?
              # String reference - look up in webhooks_config and normalize types
              {
                url          = tostring(lookup(local.webhooks_config, tostring(entry), { url = null }).url)
                content_type = tostring(lookup(lookup(local.webhooks_config, tostring(entry), {}), "content_type", "json"))
                secret       = try(tostring(lookup(local.webhooks_config, tostring(entry), {}).secret), null)
                events       = tolist(lookup(lookup(local.webhooks_config, tostring(entry), {}), "events", []))
                active       = tobool(lookup(lookup(local.webhooks_config, tostring(entry), {}), "active", true))
                insecure_ssl = tobool(lookup(lookup(local.webhooks_config, tostring(entry), {}), "insecure_ssl", false))
              } :
              # Inline definition
              {
                url          = tostring(lookup(entry, "url", null))
                content_type = tostring(lookup(entry, "content_type", "json"))
                secret       = try(tostring(lookup(entry, "secret", null)), null)
                events       = tolist(lookup(entry, "events", []))
                active       = tobool(lookup(entry, "active", true))
                insecure_ssl = tobool(lookup(entry, "insecure_ssl", false))
              }
            )
            if(can(tostring(entry)) ? tostring(entry) : lookup(entry, "name", "")) != ""
          }
        ],
        # Add repo-specific webhooks (repo overrides group by name)
        [
          {
            for entry in lookup(repo_config, "webhooks", []) :
            (can(tostring(entry)) ? tostring(entry) : lookup(entry, "name", "")) => (
              can(tostring(entry)) ?
              # String reference - look up in webhooks_config and normalize types
              {
                url          = tostring(lookup(local.webhooks_config, tostring(entry), { url = null }).url)
                content_type = tostring(lookup(lookup(local.webhooks_config, tostring(entry), {}), "content_type", "json"))
                secret       = try(tostring(lookup(local.webhooks_config, tostring(entry), {}).secret), null)
                events       = tolist(lookup(lookup(local.webhooks_config, tostring(entry), {}), "events", []))
                active       = tobool(lookup(lookup(local.webhooks_config, tostring(entry), {}), "active", true))
                insecure_ssl = tobool(lookup(lookup(local.webhooks_config, tostring(entry), {}), "insecure_ssl", false))
              } :
              # Inline definition
              {
                url          = tostring(lookup(entry, "url", null))
                content_type = tostring(lookup(entry, "content_type", "json"))
                secret       = try(tostring(lookup(entry, "secret", null)), null)
                events       = tolist(lookup(entry, "events", []))
                active       = tobool(lookup(entry, "active", true))
                insecure_ssl = tobool(lookup(entry, "insecure_ssl", false))
              }
            )
            if(can(tostring(entry)) ? tostring(entry) : lookup(entry, "name", "")) != ""
          }
        ]
      )...
    )
  }

  # Filter out any null webhooks (undefined references) and resolve secrets from webhook_secrets variable
  # Secrets using env:VAR_NAME pattern are looked up in var.webhook_secrets map
  merged_webhooks = {
    for repo_name, webhooks in local.merged_webhooks_raw : repo_name => {
      for name, webhook in webhooks : name => {
        url          = webhook.url
        content_type = webhook.content_type
        # Resolve env:VAR_NAME pattern for secrets using webhook_secrets variable
        secret = (
          webhook.secret != null && can(regex("^env:", webhook.secret)) ?
          lookup(var.webhook_secrets, substr(webhook.secret, 4, -1), null) :
          webhook.secret
        )
        events       = webhook.events
        active       = webhook.active
        insecure_ssl = webhook.insecure_ssl
      }
      if webhook != null
    }
  }



  # Transform YAML repos into the format expected by the module
  # Multiple groups are applied sequentially with proper merging
  repositories = {
    for repo_name, repo_config in local.repos_yaml : repo_name => {
      name         = repo_name
      description  = repo_config.description
      homepage_url = lookup(repo_config, "homepage_url", lookup(local.merged_configs[repo_name], "homepage_url", null))
      config_group = join(", ", repo_config.groups) # Store all groups for reference

      # Apply repo-specific overrides, falling back to merged group config
      visibility                  = lookup(repo_config, "visibility", lookup(local.merged_configs[repo_name], "visibility", "private"))
      has_wiki                    = lookup(repo_config, "has_wiki", lookup(local.merged_configs[repo_name], "has_wiki", false))
      has_issues                  = lookup(repo_config, "has_issues", lookup(local.merged_configs[repo_name], "has_issues", false))
      has_projects                = lookup(repo_config, "has_projects", lookup(local.merged_configs[repo_name], "has_projects", false))
      has_discussions             = lookup(repo_config, "has_discussions", lookup(local.merged_configs[repo_name], "has_discussions", false))
      allow_merge_commit          = lookup(repo_config, "allow_merge_commit", lookup(local.merged_configs[repo_name], "allow_merge_commit", true))
      allow_squash_merge          = lookup(repo_config, "allow_squash_merge", lookup(local.merged_configs[repo_name], "allow_squash_merge", true))
      allow_rebase_merge          = lookup(repo_config, "allow_rebase_merge", lookup(local.merged_configs[repo_name], "allow_rebase_merge", true))
      allow_auto_merge            = lookup(repo_config, "allow_auto_merge", lookup(local.merged_configs[repo_name], "allow_auto_merge", false))
      allow_update_branch         = lookup(repo_config, "allow_update_branch", lookup(local.merged_configs[repo_name], "allow_update_branch", false))
      delete_branch_on_merge      = lookup(repo_config, "delete_branch_on_merge", lookup(local.merged_configs[repo_name], "delete_branch_on_merge", false))
      web_commit_signoff_required = lookup(repo_config, "web_commit_signoff_required", lookup(local.merged_configs[repo_name], "web_commit_signoff_required", false))
      vulnerability_alerts        = lookup(repo_config, "vulnerability_alerts", lookup(local.merged_configs[repo_name], "vulnerability_alerts", true))

      # License template - optional, can be set in group or repo
      license_template = lookup(repo_config, "license_template", lookup(local.merged_configs[repo_name], "license_template", null))

      # Topics: merge from all groups + repo-specific topics
      topics = distinct(concat(
        local.merged_topics[repo_name],
        lookup(repo_config, "topics", [])
      ))

      # Teams: merge from all groups + repo-specific teams (repo overrides group)
      teams = merge(
        local.merged_teams[repo_name],
        lookup(repo_config, "teams", {})
      )

      # Collaborators: merge from all groups + repo-specific collaborators (repo overrides group)
      collaborators = merge(
        local.merged_collaborators[repo_name],
        lookup(repo_config, "collaborators", {})
      )

      # Rulesets: apply rulesets from groups and repo-specific rulesets
      # Note: effective_rulesets filters based on subscription tier
      rulesets = local.effective_rulesets[repo_name]

      # Actions: apply actions configuration from groups and repo-specific settings
      # Returns null if no actions config is specified (resource will be skipped)
      actions = local.effective_actions[repo_name]

      # Webhooks: merge from all groups + repo-specific webhooks (repo overrides group by name)
      webhooks = local.merged_webhooks[repo_name]

      # Branch protections: merge from all groups + repo-specific (repo overrides group by name)
      branch_protections = local.merged_branch_protections[repo_name]

    }
  }
}

# Validate no duplicate top-level team slugs across config/team/*.yml files
# Last-file-wins merge silently drops definitions when two files share a top-level slug.
check "duplicate_team_file_slugs" {
  assert {
    condition     = length(local.duplicate_team_slugs) == 0
    error_message = "Duplicate top-level team slugs found across config/team/ files: ${join(", ", keys(local.duplicate_team_slugs))}. Each team slug must appear in only one file."
  }
}

# Validate no duplicate team slugs across tiers (cross-tier check)
# Catches cases where a slug appears in multiple tiers (e.g. tier 0 and tier 1).
check "team_slug_uniqueness" {
  assert {
    condition = (
      length(local.all_teams) ==
      length(local.tier_0_teams) + length(local.tier_1_teams) + length(local.tier_2_teams)
    )
    error_message = "Duplicate team slugs detected across hierarchy levels. Each team slug must be unique."
  }
}

# Validate no duplicate slugs within a tier (intra-tier check)
# merge([...]) silently drops one entry when two parents share a child slug.
# These checks compare the post-merge count with the raw pre-merge count.
check "team_slug_uniqueness_intra_tier" {
  assert {
    condition = (
      length(local.tier_1_teams) == local.tier_1_raw_count &&
      length(local.tier_2_teams) == local.tier_2_raw_count
    )
    error_message = "Duplicate team slugs detected within a tier. Two parent teams cannot have child teams with the same slug."
  }
}

# Validate no user appears in both members and maintainers for any team
check "team_member_maintainer_overlap" {
  assert {
    condition = length([
      for slug, team in local.all_teams : slug
      if length(setintersection(toset(team.members), toset(team.maintainers))) > 0
    ]) == 0
    error_message = "Some teams have users in both members and maintainers. A user can only have one role per team."
  }
}

# Validate no teams nested deeper than 3 levels
# This checks that tier 2 teams have no nested `teams` key with content
check "team_nesting_depth" {
  assert {
    condition = length(flatten([
      for parent_slug, parent_config in local.teams_config_raw : flatten([
        for child_slug, child_config in lookup(parent_config, "teams", {}) : [
          for grandchild_slug, grandchild_config in lookup(child_config, "teams", {}) :
          grandchild_slug
          if length(lookup(grandchild_config, "teams", {})) > 0
        ]
      ])
    ])) == 0
    error_message = "Team nesting exceeds maximum depth of 3 levels. Reorganize your team hierarchy."
  }
}

# Validate that all requested partition names correspond to existing subdirectories
check "valid_partitions" {
  assert {
    condition     = length(local.invalid_partition_names) == 0
    error_message = "Invalid partition name(s): ${join(", ", local.invalid_partition_names)}. Available partitions: ${join(", ", sort(tolist(local.repository_partition_dirs)))}. Check config/repository/ for valid subdirectory names."
  }
}

# Validate that all org_webhook references are defined in config/webhook/
check "org_webhook_references" {
  assert {
    condition     = length(local.invalid_org_webhook_refs) == 0
    error_message = <<-EOT
      Invalid org_webhook references found in config.yml:
      ${join("\n      ", [for name in local.invalid_org_webhook_refs : "- '${name}' is not defined in config/webhook/"])}

      Available webhooks: ${join(", ", keys(local.webhooks_config))}
    EOT
  }
}

# Validate that all referenced templates exist
check "template_references" {
  assert {
    condition = length(local.invalid_template_refs) == 0
    error_message = <<-EOT
      Invalid template references found:
      ${join("\n      ", [
    for ref in local.invalid_template_refs :
    "Repository '${ref.repo}' references template '${ref.template}' which does not exist in ${var.config_path}/ruleset/templates.yml"
])}

      Available templates: ${join(", ", keys(local.ruleset_templates))}
    EOT
}
}

# Validate that all referenced branch protections exist in branch_protections_config
check "branch_protection_references" {
  assert {
    condition = length(local.invalid_branch_protection_refs) == 0
    error_message = <<-EOT
      Undefined branch protection references found:
      ${join("\n      ", [
    for ref in local.invalid_branch_protection_refs :
    "Repository '${ref.repo}' references branch protection '${ref.entry}' which is not defined in ${var.config_path}/branch-protection/"
])}

      Available branch protections: ${length(keys(local.branch_protections_config)) > 0 ? join(", ", keys(local.branch_protections_config)) : "(none defined)"}
    EOT
}
}
