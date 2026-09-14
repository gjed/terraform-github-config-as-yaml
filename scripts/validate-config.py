#!/usr/bin/env python3
"""
Validate YAML configuration files for GitHub organization management.

Usage:
    python scripts/validate-config.py
    python scripts/validate-config.py --strict
"""

from __future__ import annotations

import re
import sys
import yaml
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "config"

# New directory structure paths
GROUP_DIR = CONFIG_DIR / "group"
REPOSITORY_DIR = CONFIG_DIR / "repository"
RULESET_DIR = CONFIG_DIR / "ruleset"
TEAM_DIR = CONFIG_DIR / "team"
MEMBERSHIP_DIR = CONFIG_DIR / "membership"
WEBHOOK_DIR = CONFIG_DIR / "webhook"
BRANCH_PROTECTION_DIR = CONFIG_DIR / "branch-protection"

VALID_VISIBILITIES = ["public", "private", "internal"]
VALID_MEMBERSHIP_ROLES = ["member", "admin"]
VALID_PERMISSIONS = ["pull", "triage", "push", "maintain", "admin"]
VALID_SUBSCRIPTIONS = ["free", "pro", "team", "enterprise"]

# Settings keys that require GitHub Enterprise subscription
ENTERPRISE_ONLY_SETTINGS = [
    "advanced_security_enabled_for_new_repositories",
    "secret_scanning_enabled_for_new_repositories",
    "secret_scanning_push_protection_enabled_for_new_repositories",
    "members_can_create_internal_repositories",
]

# All valid settings keys (used for schema validation).
# Note: two_factor_requirement is intentionally excluded — the GitHub Terraform provider
# (~> 6.0) does not expose it as a resource attribute. Use the GitHub org security UI instead.
VALID_SETTINGS_KEYS = [
    "billing_email",
    "company",
    "blog",
    "email",
    "location",
    "description",
    "default_repository_permission",
    "members_can_create_repositories",
    "members_can_create_public_repositories",
    "members_can_create_private_repositories",
    "members_can_fork_private_repositories",
    "web_commit_signoff_required",
    "dependabot_alerts_enabled_for_new_repositories",
    "dependabot_security_updates_enabled_for_new_repositories",
    "dependency_graph_enabled_for_new_repositories",
] + ENTERPRISE_ONLY_SETTINGS

VALID_DEFAULT_REPOSITORY_PERMISSIONS = ["none", "read", "write", "admin"]

VALID_RULE_TYPES = [
    "deletion",
    "non_fast_forward",
    "required_linear_history",
    "required_signatures",
    "pull_request",
    "required_status_checks",
    "creation",
    "update",
    "required_deployments",
    "branch_name_pattern",
    "commit_message_pattern",
    "commit_author_email_pattern",
    "committer_email_pattern",
]
VALID_SCOPES = ["organization", "repository"]

VALID_TEAM_PRIVACIES = ["closed", "secret"]
VALID_DELEGATION_ALGORITHMS = ["round_robin", "load_balance"]


def load_yaml(filepath: Path) -> dict:
    """Load and parse a YAML file."""
    try:
        with open(filepath) as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {filepath}: {e}")


def load_yaml_directory(directory: Path) -> dict:
    """Load and merge all YAML files from a directory."""
    if not directory.exists():
        return {}

    merged = {}
    for filepath in sorted(directory.glob("*.yml")):
        content = load_yaml(filepath)
        if content:
            merged.update(content)
    return merged


def load_repository_config(directory: Path, requested_partitions: list[str]) -> dict:
    """Load repository definitions, including partition subdirectories.

    Mirrors the partition-aware file collection in yaml-config.tf:
    top-level *.yml files are always loaded, plus *.yml from each active
    partition subdirectory. An empty `requested_partitions` means all
    discovered partitions are active.
    """
    if not directory.exists():
        return {}

    merged = load_yaml_directory(directory)

    available = sorted(d.name for d in directory.iterdir() if d.is_dir())
    active = (
        available
        if not requested_partitions
        else [p for p in available if p in requested_partitions]
    )

    for partition in active:
        merged.update(load_yaml_directory(directory / partition))

    return merged


def split_rulesets_by_scope(rulesets: dict) -> tuple[dict, dict]:
    """Split rulesets into repo-scoped and org-scoped maps.

    Returns (repo_rulesets, org_rulesets).
    Definitions without 'scope' or with 'scope: repository' are repo-scoped.
    Definitions with 'scope: organization' are org-scoped.
    """
    repo_rulesets = {}
    org_rulesets = {}
    for name, config in rulesets.items():
        if isinstance(config, dict) and config.get("scope") == "organization":
            org_rulesets[name] = config
        else:
            repo_rulesets[name] = config
    return repo_rulesets, org_rulesets


def validate_config(config: dict, webhooks: dict) -> tuple[list[str], list[str]]:
    """Validate config.yml. Returns (errors, warnings)."""
    errors = []
    warnings = []

    if "organization" not in config:
        errors.append("config.yml: Missing required field 'organization'")

    subscription = config.get("subscription", "free")
    if subscription not in VALID_SUBSCRIPTIONS:
        errors.append(f"config.yml: Invalid subscription '{subscription}'")

    # Validate org_webhooks references
    is_organization = config.get("is_organization", True)
    org_webhooks = config.get("org_webhooks", [])
    if org_webhooks:
        if not isinstance(org_webhooks, list) or not all(
            isinstance(n, str) for n in org_webhooks
        ):
            errors.append(
                "config.yml: 'org_webhooks' must be a list of webhook name strings, "
                f"got {type(org_webhooks).__name__}"
            )
        else:
            if not is_organization:
                warnings.append(
                    "config.yml: 'org_webhooks' is set but 'is_organization' is false — "
                    "org webhooks will not be created for personal accounts"
                )
            for name in org_webhooks:
                if name not in webhooks:
                    errors.append(
                        f"config.yml: org_webhooks references '{name}' which is not defined in config/webhook/"
                    )
                elif not webhooks[name].get("events"):
                    errors.append(
                        f"config/webhook/{name}: 'events' must define at least one event "
                        "(required by the GitHub provider)"
                    )

    # Validate optional security section
    security = config.get("security")
    if security is not None:
        if not isinstance(security, dict):
            errors.append("config.yml: 'security' must be a mapping")
        else:
            # Warn on unknown keys — the section is narrow enough to make typos detectable cheaply
            known_security_keys = {"security_manager_teams"}
            unknown_keys = set(security.keys()) - known_security_keys
            if unknown_keys:
                warnings.append(
                    f"config.yml: Unknown key(s) in 'security': {', '.join(sorted(unknown_keys))}"
                )

            # Use key presence check rather than .get() to distinguish an absent key
            # from one explicitly set to null — the latter is invalid for Terraform (toset(null) errors).
            if "security_manager_teams" in security:
                teams = security["security_manager_teams"]
                if teams is None:
                    errors.append(
                        "config.yml: 'security.security_manager_teams' must be a list, not null "
                        "(use [] for an empty list)"
                    )
                elif not isinstance(teams, list):
                    errors.append(
                        "config.yml: 'security.security_manager_teams' must be a list"
                    )
                else:
                    for i, team in enumerate(teams):
                        if not isinstance(team, str):
                            errors.append(
                                f"config.yml: 'security.security_manager_teams[{i}]' must be a string, got {type(team).__name__}"
                            )
                    # Tier warning is informational — emit regardless of other unrelated errors
                    # so users always see it on re-run after fixing separate issues.
                    if len(teams) > 0 and subscription in ["free", "pro"]:
                        warnings.append(
                            f"config.yml: security_manager_teams configured but subscription '{subscription}' "
                            "does not support security manager roles (requires 'team' or 'enterprise') — "
                            "resources will be skipped"
                        )

    return errors, warnings


def validate_settings(config: dict) -> tuple[list[str], list[str]]:
    """5.1-5.3 Validate optional settings: block in config.yml.

    Returns (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    settings = config.get("settings")
    if settings is None:
        return errors, warnings

    if not isinstance(settings, dict):
        errors.append("config.yml: 'settings' must be a mapping")
        return errors, warnings

    subscription = config.get("subscription", "free")
    is_organization = config.get("is_organization", True)

    # Warn when settings: is present but is_organization: false — Terraform will silently ignore it
    if not is_organization:
        warnings.append(
            "config.yml: 'settings' block is present but 'is_organization' is false — "
            "organization settings will not be applied (Terraform ignores them for personal accounts)"
        )

    # 5.1 Check for unknown keys
    for key in settings:
        if key not in VALID_SETTINGS_KEYS:
            # Give a specific, actionable message for two_factor_requirement
            if key == "two_factor_requirement":
                errors.append(
                    "config.yml: settings.two_factor_requirement is not managed by Terraform "
                    "(the integrations/github provider ~> 6.0 does not expose this attribute). "
                    "Configure two-factor requirement via the GitHub organization security settings UI. "
                    "See docs/CONFIGURATION.md for details."
                )
            else:
                errors.append(f"config.yml: settings: unknown key '{key}'")

    # billing_email is required by the provider when the settings block is active
    billing_email = settings.get("billing_email")
    if not isinstance(billing_email, str) or not billing_email.strip():
        errors.append(
            "config.yml: settings.billing_email is required when 'settings' is present"
        )

    # Validate default_repository_permission value
    perm = settings.get("default_repository_permission")
    if perm is not None and perm not in VALID_DEFAULT_REPOSITORY_PERMISSIONS:
        errors.append(
            f"config.yml: settings.default_repository_permission: "
            f"invalid value '{perm}' (must be one of: "
            f"{', '.join(VALID_DEFAULT_REPOSITORY_PERMISSIONS)})"
        )

    # 5.2 Warn when enterprise-only settings are present on non-enterprise tiers
    if subscription != "enterprise":
        skipped = [k for k in ENTERPRISE_ONLY_SETTINGS if k in settings]
        if skipped:
            warnings.append(
                f"config.yml: settings: enterprise-only settings will be "
                f"skipped on '{subscription}' tier: {', '.join(skipped)}"
            )

    return errors, warnings


def validate_groups(groups: dict, org_ruleset_names: set) -> list[str]:
    """Validate groups configuration."""
    errors = []

    for group_name, group_config in groups.items():
        if not isinstance(group_config, dict):
            errors.append(f"groups: Group '{group_name}' must be a dictionary")
            continue

        # Validate visibility if specified
        visibility = group_config.get("visibility")
        if visibility and visibility not in VALID_VISIBILITIES:
            errors.append(
                f"groups: Group '{group_name}' has invalid visibility '{visibility}'"
            )

        # Validate teams if specified
        teams = group_config.get("teams", {})
        if teams:
            for team, permission in teams.items():
                if permission not in VALID_PERMISSIONS:
                    errors.append(
                        f"groups: Group '{group_name}' team '{team}' has invalid permission '{permission}'"
                    )

        # Org rulesets must not be assigned to groups via rulesets:
        for ruleset_entry in group_config.get("rulesets", []):
            if isinstance(ruleset_entry, str):
                entry_name = ruleset_entry
            elif isinstance(ruleset_entry, dict):
                entry_name = ruleset_entry.get("template", "")
            else:
                errors.append(
                    f"groups: Group '{group_name}' has invalid ruleset entry "
                    f"'{ruleset_entry}' (must be a string or dictionary)"
                )
                continue
            if entry_name in org_ruleset_names:
                errors.append(
                    f"groups: Group '{group_name}' references org-scoped ruleset '{entry_name}' "
                    f"via 'rulesets:' — org rulesets apply globally and cannot be assigned per-group"
                )

    return errors


def validate_repositories(
    repos: dict, groups: dict, repo_rulesets: dict, org_ruleset_names: set
) -> list[str]:
    """Validate repositories configuration."""
    errors = []

    for repo_name, repo_config in repos.items():
        if not isinstance(repo_config, dict):
            errors.append(
                f"repositories: Repository '{repo_name}' must be a dictionary"
            )
            continue

        # Check required fields
        if "description" not in repo_config:
            errors.append(
                f"repositories: Repository '{repo_name}' missing 'description'"
            )

        if "groups" not in repo_config:
            errors.append(f"repositories: Repository '{repo_name}' missing 'groups'")
        else:
            # Validate group references
            for group in repo_config["groups"]:
                if group not in groups:
                    errors.append(
                        f"repositories: Repository '{repo_name}' references unknown group '{group}'"
                    )

        # Validate visibility if specified
        visibility = repo_config.get("visibility")
        if visibility and visibility not in VALID_VISIBILITIES:
            errors.append(
                f"repositories: Repository '{repo_name}' has invalid visibility '{visibility}'"
            )

        # Validate teams if specified
        teams = repo_config.get("teams", {})
        for team, permission in teams.items():
            if permission not in VALID_PERMISSIONS:
                errors.append(
                    f"repositories: Repository '{repo_name}' team '{team}' has invalid permission '{permission}'"
                )

        # Validate ruleset references
        for ruleset_entry in repo_config.get("rulesets", []):
            # Handle both string references and template references
            if isinstance(ruleset_entry, str):
                if ruleset_entry in org_ruleset_names:
                    errors.append(
                        f"repositories: Repository '{repo_name}' references org-scoped ruleset '{ruleset_entry}' "
                        f"via 'rulesets:' — org rulesets apply globally and cannot be assigned per-repository"
                    )
                elif ruleset_entry not in repo_rulesets:
                    errors.append(
                        f"repositories: Repository '{repo_name}' references unknown ruleset '{ruleset_entry}'"
                    )
            elif isinstance(ruleset_entry, dict) and "template" in ruleset_entry:
                template_name = ruleset_entry["template"]
                if template_name in org_ruleset_names:
                    errors.append(
                        f"repositories: Repository '{repo_name}' references org-scoped ruleset '{template_name}' "
                        f"via 'rulesets:' — org rulesets apply globally and cannot be assigned per-repository"
                    )
                elif template_name not in repo_rulesets:
                    errors.append(
                        f"repositories: Repository '{repo_name}' references unknown template '{template_name}'"
                    )

    return errors


def validate_rulesets(rulesets: dict) -> list[str]:
    """Validate rulesets configuration."""
    errors = []

    for ruleset_name, ruleset_config in rulesets.items():
        if not isinstance(ruleset_config, dict):
            errors.append(f"rulesets: Ruleset '{ruleset_name}' must be a dictionary")
            continue

        # Validate scope if specified
        scope = ruleset_config.get("scope")
        if scope is not None and scope not in VALID_SCOPES:
            errors.append(
                f"rulesets: Ruleset '{ruleset_name}' has invalid scope '{scope}' "
                f"(valid: {', '.join(VALID_SCOPES)})"
            )

        # Check required fields
        if "target" not in ruleset_config:
            errors.append(f"rulesets: Ruleset '{ruleset_name}' missing 'target'")
        elif ruleset_config["target"] not in ["branch", "tag"]:
            errors.append(
                f"rulesets: Ruleset '{ruleset_name}' has invalid target '{ruleset_config['target']}'"
            )

        if "enforcement" not in ruleset_config:
            errors.append(f"rulesets: Ruleset '{ruleset_name}' missing 'enforcement'")
        elif ruleset_config["enforcement"] not in ["active", "evaluate", "disabled"]:
            errors.append(
                f"rulesets: Ruleset '{ruleset_name}' has invalid enforcement '{ruleset_config['enforcement']}'"
            )

        if "conditions" not in ruleset_config:
            errors.append(f"rulesets: Ruleset '{ruleset_name}' missing 'conditions'")

        if "rules" not in ruleset_config:
            errors.append(f"rulesets: Ruleset '{ruleset_name}' missing 'rules'")
        else:
            is_org_scoped = ruleset_config.get("scope") == "organization"
            for rule in ruleset_config["rules"]:
                if "type" not in rule:
                    errors.append(
                        f"rulesets: Ruleset '{ruleset_name}' has rule without 'type'"
                    )
                elif rule["type"] not in VALID_RULE_TYPES:
                    errors.append(
                        f"rulesets: Ruleset '{ruleset_name}' has invalid rule type '{rule['type']}'"
                    )
                elif is_org_scoped and rule["type"] == "required_deployments":
                    errors.append(
                        f"rulesets: Org-scoped ruleset '{ruleset_name}' uses rule type "
                        f"'required_deployments' which is not supported for organization rulesets"
                    )

    return errors


_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$")


def load_team_directory(directory: Path) -> dict:
    """Load team configs with per-file duplicate slug detection.

    Unlike load_yaml_directory (which silently overwrites duplicates), this
    raises ValueError when the same top-level slug appears in more than one file.
    """
    teams: dict = {}
    sources: dict = {}
    for team_file in sorted(directory.glob("*.yml")):
        file_teams = load_yaml(team_file)
        if not file_teams:
            continue
        if not isinstance(file_teams, dict):
            raise ValueError(
                f"Team configuration file must contain a mapping: {team_file.name}"
            )
        for slug, team_config in file_teams.items():
            if slug in teams:
                raise ValueError(
                    f"Duplicate top-level team slug '{slug}' found in "
                    f"'{sources[slug].name}' and '{team_file.name}'. "
                    f"Each team slug must appear in only one file."
                )
            teams[slug] = team_config
            sources[slug] = team_file
    return teams


def flatten_teams(
    teams: dict, depth: int = 0, parent: str | None = None
) -> tuple[list[dict], list[str]]:
    """Recursively flatten nested team definitions.

    Returns (flat_list, type_errors) so callers learn about malformed entries
    instead of silently skipping them.
    """
    result: list[dict] = []
    errors: list[str] = []

    for slug, config in teams.items():
        if not isinstance(config, dict):
            errors.append(
                f"teams: Team '{slug}' configuration must be a mapping, "
                f"got {type(config).__name__!r}"
            )
            continue

        result.append(
            {"slug": slug, "config": config, "depth": depth, "parent": parent}
        )

        nested = config.get("teams")
        if nested is None:
            pass  # key absent or explicitly null — treat as no children
        elif isinstance(nested, dict):
            child_result, child_errors = flatten_teams(nested, depth + 1, slug)
            result.extend(child_result)
            errors.extend(child_errors)
        else:
            errors.append(
                f"teams: Team '{slug}' field 'teams' must be a mapping, "
                f"got {type(nested).__name__!r}"
            )

    return result, errors


def validate_teams(
    teams: dict,
    flat_teams: list[dict] | None = None,
    flat_errors: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Validate teams configuration. Returns (errors, warnings).

    Pass pre-computed flat_teams / flat_errors to avoid re-flattening.
    """
    errors: list[str] = list(flat_errors or [])
    warnings: list[str] = []

    if not teams:
        return errors, warnings

    if flat_teams is None:
        flat_teams, type_errors = flatten_teams(teams)
        errors.extend(type_errors)

    # Check for duplicate slugs across the hierarchy
    seen: set[str] = set()
    for t in flat_teams:
        slug = t["slug"]
        if slug in seen:
            errors.append(f"teams: Duplicate team slug '{slug}' found across hierarchy")
        seen.add(slug)

    # Check max nesting depth
    for t in flat_teams:
        if t["depth"] > 2:
            errors.append(
                f"teams: Team '{t['slug']}' exceeds maximum nesting depth of 3 levels "
                f"(depth {t['depth'] + 1})"
            )

    # Field-level validation
    for t in flat_teams:
        slug = t["slug"]
        config = t["config"]

        # Slug format (GitHub normalises slugs; mismatches cause perpetual plan diff)
        if not _SLUG_RE.match(slug):
            errors.append(
                f"teams: Team slug '{slug}' contains invalid characters. "
                f"Use only lowercase letters, digits, and hyphens; "
                f"must not start or end with a hyphen (e.g. 'platform-team')."
            )

        if "description" not in config:
            errors.append(f"teams: Team '{slug}' missing required field 'description'")

        privacy = config.get("privacy")
        if privacy is not None:
            if not isinstance(privacy, str):
                errors.append(
                    f"teams: Team '{slug}' field 'privacy' must be a string, "
                    f"got {type(privacy).__name__!r}"
                )
            elif privacy not in VALID_TEAM_PRIVACIES:
                errors.append(
                    f"teams: Team '{slug}' has invalid privacy '{privacy}'. "
                    f"Valid values: {', '.join(VALID_TEAM_PRIVACIES)}"
                )

        # members / maintainers: must be list of strings when present
        for field in ("members", "maintainers"):
            value = config.get(field)
            if value is None:
                continue
            if not isinstance(value, list):
                errors.append(
                    f"teams: Team '{slug}' field '{field}' must be a list, "
                    f"got {type(value).__name__!r}"
                )
            elif not all(isinstance(u, str) for u in value):
                errors.append(
                    f"teams: Team '{slug}' field '{field}' must be a list of strings"
                )

        # Overlap check (only when both are valid lists)
        raw_members = config.get("members")
        raw_maintainers = config.get("maintainers")
        if isinstance(raw_members, list) and isinstance(raw_maintainers, list):
            overlap = set(raw_members) & set(raw_maintainers)
            if overlap:
                errors.append(
                    f"teams: Team '{slug}' has users in both members and maintainers: "
                    f"{', '.join(sorted(overlap))}"
                )

        # review_request_delegation: full type + value validation
        raw_delegation = config.get("review_request_delegation")
        if raw_delegation is not None:
            if not isinstance(raw_delegation, dict):
                errors.append(
                    f"teams: Team '{slug}' field 'review_request_delegation' must be "
                    f"a mapping, got {type(raw_delegation).__name__!r}"
                )
            else:
                delegation = raw_delegation

                enabled = delegation.get("enabled")
                if enabled is not None and not isinstance(enabled, bool):
                    errors.append(
                        f"teams: Team '{slug}' field "
                        f"'review_request_delegation.enabled' must be a boolean"
                    )

                algorithm = delegation.get("algorithm")
                if algorithm is not None:
                    if not isinstance(algorithm, str):
                        errors.append(
                            f"teams: Team '{slug}' field "
                            f"'review_request_delegation.algorithm' must be a string"
                        )
                    elif algorithm not in VALID_DELEGATION_ALGORITHMS:
                        errors.append(
                            f"teams: Team '{slug}' has invalid delegation algorithm "
                            f"'{algorithm}'. Valid values: "
                            f"{', '.join(VALID_DELEGATION_ALGORITHMS)}"
                        )

                member_count = delegation.get("member_count")
                if member_count is not None:
                    if not isinstance(member_count, int) or isinstance(
                        member_count, bool
                    ):
                        errors.append(
                            f"teams: Team '{slug}' field "
                            f"'review_request_delegation.member_count' must be an integer"
                        )
                    elif member_count <= 0:
                        errors.append(
                            f"teams: Team '{slug}' field "
                            f"'review_request_delegation.member_count' must be greater than 0"
                        )

                notify = delegation.get("notify")
                if notify is not None and not isinstance(notify, bool):
                    errors.append(
                        f"teams: Team '{slug}' field "
                        f"'review_request_delegation.notify' must be a boolean"
                    )

    return errors, warnings


def check_team_cross_references(
    repos: dict, groups: dict, managed_team_slugs: set
) -> list[str]:
    """Warn when repos/groups reference team slugs not in config/team/."""
    warnings = []

    if not managed_team_slugs:
        return warnings

    # Collect all referenced team slugs from repos and groups
    referenced = set()
    for repo_name, repo_config in repos.items():
        if isinstance(repo_config, dict):
            for slug in repo_config.get("teams", {}).keys():
                referenced.add((slug, f"repository '{repo_name}'"))

    for group_name, group_config in groups.items():
        if isinstance(group_config, dict):
            for slug in group_config.get("teams", {}).keys():
                referenced.add((slug, f"group '{group_name}'"))

    for slug, source in referenced:
        if slug not in managed_team_slugs:
            warnings.append(
                f"teams: {source} references team '{slug}' which is not defined in "
                f"config/team/ (may be managed externally)"
            )

    return warnings


def validate_membership(members: dict) -> list[str]:
    """Validate membership configuration."""
    errors = []

    for username, role in members.items():
        if not isinstance(username, str) or not username:
            errors.append(
                f"membership: Entry '{username}' has an invalid username (must be a non-empty string)"
            )
            continue

        if not isinstance(role, str):
            errors.append(
                f"membership: Member '{username}' has invalid role type '{type(role).__name__}' (must be a string)"
            )
        elif role not in VALID_MEMBERSHIP_ROLES:
            errors.append(
                f"membership: Member '{username}' has invalid role '{role}' "
                f"(valid roles: {', '.join(VALID_MEMBERSHIP_ROLES)})"
            )

    return errors


# Boolean fields on branch protection definitions
_BRANCH_PROTECTION_BOOL_FIELDS = [
    "enforce_admins",
    "allows_deletions",
    "allows_force_pushes",
    "lock_branch",
    "require_conversation_resolution",
    "require_signed_commits",
    "required_linear_history",
]

# Boolean fields inside required_pull_request_reviews
_PR_REVIEW_BOOL_FIELDS = [
    "dismiss_stale_reviews",
    "require_code_owner_reviews",
    "require_last_push_approval",
    "restrict_dismissals",
]


def validate_branch_protections(branch_protections: dict) -> list[str]:
    """Validate branch protection definitions from config/branch-protection/.

    Returns a list of error messages.
    """
    errors: list[str] = []

    for name, config in branch_protections.items():
        if not isinstance(config, dict):
            errors.append(
                f"branch-protection: '{name}' must be a mapping, "
                f"got {type(config).__name__}"
            )
            continue

        # pattern is the only required field
        pattern = config.get("pattern")
        if pattern is None:
            errors.append(
                f"branch-protection: '{name}' missing required field 'pattern'"
            )
        elif not isinstance(pattern, str):
            errors.append(
                f"branch-protection: '{name}' field 'pattern' must be a string, "
                f"got {type(pattern).__name__}"
            )

        # Validate boolean fields
        for field in _BRANCH_PROTECTION_BOOL_FIELDS:
            value = config.get(field)
            if value is not None and not isinstance(value, bool):
                errors.append(
                    f"branch-protection: '{name}' field '{field}' must be a boolean, "
                    f"got {type(value).__name__}"
                )

        # Validate required_pull_request_reviews sub-block
        pr_reviews = config.get("required_pull_request_reviews")
        if pr_reviews is not None:
            if not isinstance(pr_reviews, dict):
                errors.append(
                    f"branch-protection: '{name}' field 'required_pull_request_reviews' "
                    f"must be a mapping, got {type(pr_reviews).__name__}"
                )
            else:
                count = pr_reviews.get("required_approving_review_count")
                if count is not None:
                    if not isinstance(count, int) or isinstance(count, bool):
                        errors.append(
                            f"branch-protection: '{name}' field "
                            f"'required_pull_request_reviews.required_approving_review_count' "
                            f"must be an integer"
                        )
                    elif count < 0:
                        errors.append(
                            f"branch-protection: '{name}' field "
                            f"'required_pull_request_reviews.required_approving_review_count' "
                            f"must be non-negative"
                        )
                for field in _PR_REVIEW_BOOL_FIELDS:
                    value = pr_reviews.get(field)
                    if value is not None and not isinstance(value, bool):
                        errors.append(
                            f"branch-protection: '{name}' field "
                            f"'required_pull_request_reviews.{field}' must be a boolean, "
                            f"got {type(value).__name__}"
                        )

        # Validate required_status_checks sub-block
        status_checks = config.get("required_status_checks")
        if status_checks is not None:
            if not isinstance(status_checks, dict):
                errors.append(
                    f"branch-protection: '{name}' field 'required_status_checks' "
                    f"must be a mapping, got {type(status_checks).__name__}"
                )
            else:
                strict = status_checks.get("strict")
                if strict is not None and not isinstance(strict, bool):
                    errors.append(
                        f"branch-protection: '{name}' field "
                        f"'required_status_checks.strict' must be a boolean, "
                        f"got {type(strict).__name__}"
                    )
                contexts = status_checks.get("contexts")
                if contexts is not None and not isinstance(contexts, list):
                    errors.append(
                        f"branch-protection: '{name}' field "
                        f"'required_status_checks.contexts' must be a list, "
                        f"got {type(contexts).__name__}"
                    )

        # Validate restrict_pushes sub-block
        restrict_pushes = config.get("restrict_pushes")
        if restrict_pushes is not None:
            if not isinstance(restrict_pushes, dict):
                errors.append(
                    f"branch-protection: '{name}' field 'restrict_pushes' "
                    f"must be a mapping, got {type(restrict_pushes).__name__}"
                )
            else:
                blocks = restrict_pushes.get("blocks_creations")
                if blocks is not None and not isinstance(blocks, bool):
                    errors.append(
                        f"branch-protection: '{name}' field "
                        f"'restrict_pushes.blocks_creations' must be a boolean, "
                        f"got {type(blocks).__name__}"
                    )

    return errors


def validate_branch_protection_references(
    repos: dict, groups: dict, branch_protections: dict
) -> list[str]:
    """Validate that branch_protections: references in groups and repos resolve.

    Returns a list of error messages.
    """
    errors: list[str] = []

    # Check group references
    for group_name, group_config in groups.items():
        if not isinstance(group_config, dict):
            continue
        for ref in group_config.get("branch_protections", []):
            if not isinstance(ref, str):
                errors.append(
                    f"groups: Group '{group_name}' has invalid branch_protections entry "
                    f"'{ref}' (must be a string)"
                )
            elif ref not in branch_protections:
                errors.append(
                    f"groups: Group '{group_name}' references unknown branch protection "
                    f"'{ref}' — not defined in config/branch-protection/"
                )

    # Check repo references
    for repo_name, repo_config in repos.items():
        if not isinstance(repo_config, dict):
            continue
        for ref in repo_config.get("branch_protections", []):
            if not isinstance(ref, str):
                errors.append(
                    f"repositories: Repository '{repo_name}' has invalid branch_protections "
                    f"entry '{ref}' (must be a string)"
                )
            elif ref not in branch_protections:
                errors.append(
                    f"repositories: Repository '{repo_name}' references unknown branch "
                    f"protection '{ref}' — not defined in config/branch-protection/"
                )

    return errors


def resolve_effective_visibility(repo_config: dict, groups: dict) -> str:
    """Resolve a repository's effective visibility after group inheritance.

    Mirrors the Terraform merge order in local.merged_configs: groups are applied in
    order with later groups overriding earlier ones, then the repo-level key wins.
    Defaults to 'private', matching local.repo_visibility.
    """
    visibility = "private"

    for group_name in repo_config.get("groups", []) or []:
        group_config = groups.get(group_name)
        if isinstance(group_config, dict) and group_config.get("visibility"):
            visibility = group_config["visibility"]

    if repo_config.get("visibility"):
        visibility = repo_config["visibility"]

    return visibility


def validate_branch_protection_tier(
    repos: dict, groups: dict, subscription: str
) -> list[str]:
    """Warn when branch protections are configured for private repos on the free tier.

    GitHub offers protected branches on private repositories only for paid plans, so
    Terraform skips them on free. Surfacing this before plan avoids a silent no-op.

    Returns a list of warning messages.
    """
    if subscription != "free":
        return []

    warnings: list[str] = []

    for repo_name, repo_config in repos.items():
        if not isinstance(repo_config, dict):
            continue

        has_protections = bool(repo_config.get("branch_protections")) or any(
            isinstance(groups.get(g), dict) and groups[g].get("branch_protections")
            for g in repo_config.get("groups", []) or []
        )
        if not has_protections:
            continue

        if resolve_effective_visibility(repo_config, groups) != "public":
            warnings.append(
                f"repositories: Repository '{repo_name}' is private and has branch "
                f"protections, but protected branches require a paid GitHub plan on "
                f"private repositories — they will be skipped by Terraform"
            )

    return warnings


def validate_partitions(
    repository_dir: Path, requested_partitions: list[str]
) -> tuple[list[str], list[str]]:
    """Validate that requested partition names correspond to existing subdirectories.

    Returns (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not requested_partitions:
        return errors, warnings

    # Discover available partition directories
    available = (
        sorted(d.name for d in repository_dir.iterdir() if d.is_dir())
        if repository_dir.exists()
        else []
    )

    invalid = [p for p in requested_partitions if p not in available]
    if invalid:
        available_str = ", ".join(available) if available else "(none)"
        errors.append(
            f"partitions: Invalid partition name(s): {', '.join(invalid)}. "
            f"Available partitions: {available_str}. "
            f"Check config/repository/ for valid subdirectory names."
        )

    # Warn about empty partition directories (valid but useless)
    for partition in requested_partitions:
        partition_path = repository_dir / partition
        if partition_path.is_dir():
            yml_files = list(partition_path.glob("*.yml"))
            if not yml_files:
                warnings.append(
                    f"partitions: Partition '{partition}' directory exists but contains "
                    f"no YAML files — it will contribute zero repositories"
                )

    return errors, warnings


def main():
    """Main validation entry point."""
    strict = "--strict" in sys.argv

    # Parse --partitions=name1,name2 argument (optional)
    requested_partitions: list[str] = []
    for arg in sys.argv[1:]:
        if arg.startswith("--partitions="):
            requested_partitions = [
                p.strip() for p in arg.split("=", 1)[1].split(",") if p.strip()
            ]

    all_errors = []
    all_warnings: list[str] = []

    print("Validating configuration files...")
    print()

    # Check config.yml exists
    config_file = CONFIG_DIR / "config.yml"
    if not config_file.exists():
        all_errors.append("Missing required file: config/config.yml")

    # Check at least one directory has content
    if not GROUP_DIR.exists() and not (CONFIG_DIR / "groups.yml").exists():
        all_errors.append(
            "Missing group configuration: need config/group/ directory or config/groups.yml"
        )

    if not REPOSITORY_DIR.exists() and not (CONFIG_DIR / "repositories.yml").exists():
        all_errors.append(
            "Missing repository configuration: need config/repository/ directory or config/repositories.yml"
        )

    if not RULESET_DIR.exists() and not (CONFIG_DIR / "rulesets.yml").exists():
        all_errors.append(
            "Missing ruleset configuration: need config/ruleset/ directory or config/rulesets.yml"
        )

    if all_errors:
        for error in all_errors:
            print(f"ERROR: {error}")
        sys.exit(1)

    # Load all config files
    try:
        config = load_yaml(config_file)

        # Load from new directory structure or fall back to old single-file structure
        if GROUP_DIR.exists():
            groups = load_yaml_directory(GROUP_DIR)
        else:
            groups = load_yaml(CONFIG_DIR / "groups.yml")

        if REPOSITORY_DIR.exists():
            repos = load_repository_config(REPOSITORY_DIR, requested_partitions)
        else:
            repos = load_yaml(CONFIG_DIR / "repositories.yml")

        if RULESET_DIR.exists():
            rulesets = load_yaml_directory(RULESET_DIR)
        else:
            rulesets = load_yaml(CONFIG_DIR / "rulesets.yml")

        # Load teams (optional directory) with per-file duplicate detection
        if TEAM_DIR.exists():
            teams = load_team_directory(TEAM_DIR)
        else:
            teams = {}
        # Membership directory is optional (load_yaml_directory handles missing dir)
        try:
            members = load_yaml_directory(MEMBERSHIP_DIR)
        except (TypeError, AttributeError) as e:
            raise ValueError(
                f"Invalid membership configuration: each YAML file in {MEMBERSHIP_DIR} "
                "must contain a top-level mapping (username: role), not a list or scalar."
            ) from e
        # Load webhook definitions (optional directory)
        webhooks = load_yaml_directory(WEBHOOK_DIR) if WEBHOOK_DIR.exists() else {}
        # Load branch protection definitions (optional directory)
        branch_protections = (
            load_yaml_directory(BRANCH_PROTECTION_DIR)
            if BRANCH_PROTECTION_DIR.exists()
            else {}
        )
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Separate rulesets by scope for targeted validation
    repo_rulesets, org_rulesets = split_rulesets_by_scope(rulesets)
    org_ruleset_names = set(org_rulesets.keys())

    # Validate each config type
    config_errors, config_warnings = validate_config(config, webhooks)
    all_errors.extend(config_errors)
    all_warnings.extend(config_warnings)
    settings_errors, settings_warnings = validate_settings(config)
    all_errors.extend(settings_errors)
    all_warnings.extend(settings_warnings)
    all_errors.extend(validate_groups(groups, org_ruleset_names))
    all_errors.extend(validate_rulesets(rulesets))
    all_errors.extend(validate_membership(members))
    all_errors.extend(validate_branch_protections(branch_protections))
    all_errors.extend(
        validate_branch_protection_references(repos, groups, branch_protections)
    )
    all_warnings.extend(
        validate_branch_protection_tier(
            repos, groups, config.get("subscription", "free")
        )
    )

    # Print SCIM/SSO reminder when membership config is present
    if members:
        print(
            "⚠️  REMINDER: Membership config detected. Do NOT use membership management "
            "alongside SCIM/IdP provisioning (Okta, Azure AD, GitHub Enterprise SCIM). "
            "They will conflict and cause unpredictable membership changes.\n"
        )

    # Flatten once; pass into validate_teams so it isn't re-computed internally
    flat_teams, flat_errors = flatten_teams(teams) if teams else ([], [])

    team_errors, team_warnings = validate_teams(
        teams, flat_teams=flat_teams, flat_errors=flat_errors
    )
    all_errors.extend(team_errors)

    # Cross-reference check for team slugs (warnings only)
    team_xref_warnings = []
    if flat_teams:
        managed_slugs = {t["slug"] for t in flat_teams}
        team_xref_warnings = check_team_cross_references(repos, groups, managed_slugs)
    all_errors.extend(
        validate_repositories(repos, groups, repo_rulesets, org_ruleset_names)
    )

    # Validate partition names when --partitions is provided
    if requested_partitions:
        partition_errors, partition_warnings = validate_partitions(
            REPOSITORY_DIR, requested_partitions
        )
        all_errors.extend(partition_errors)
        all_warnings.extend(partition_warnings)

    # Warn about subscription tier and org rulesets
    subscription = config.get("subscription", "free")
    if org_rulesets and subscription in ("free", "pro"):
        print(
            f"WARNING: {len(org_rulesets)} org ruleset(s) defined but subscription is '{subscription}' "
            f"— org rulesets require 'team' or 'enterprise' and will be skipped by Terraform."
        )
        print()

    # Report warnings
    if all_warnings:
        print("Warnings:")
        print()
        for warning in all_warnings:
            print(f"  ⚠  {warning}")
        print()
        # --strict: treat warnings as errors
        if strict:
            print(f"Strict mode: {len(all_warnings)} warning(s) treated as error(s)")
            sys.exit(1)

    # Report warnings (non-fatal)
    if all_warnings:
        for warning in all_warnings:
            print(f"WARNING: {warning}")
        print()

    # Report results
    if all_errors:
        print("Validation FAILED:")
        print()
        for error in all_errors:
            print(f"  - {error}")
        print()
        print(f"Found {len(all_errors)} error(s)")
        sys.exit(1)
    else:
        print("Validation PASSED")
        print()
        print(f"  - Organization: {config.get('organization', 'not set')}")
        print(f"  - Subscription: {config.get('subscription', 'free')}")
        has_settings = "settings" in config
        print(f"  - Org settings: {'configured' if has_settings else 'not configured'}")
        print(f"  - Groups: {len(groups)}")
        print(f"  - Repositories: {len(repos)}")
        print(f"  - Rulesets: {len(rulesets)}")
        print(f"  - Branch protections: {len(branch_protections)}")
        print(f"  - Teams: {len(flat_teams)}")
        org_webhooks = config.get("org_webhooks", [])
        if org_webhooks:
            print(f"  - Org webhooks: {len(org_webhooks)} ({', '.join(org_webhooks)})")

        if members:
            print(f"  - Members: {len(members)}")

        security = config.get("security", {})
        sec_teams = (
            security.get("security_manager_teams", [])
            if isinstance(security, dict)
            else []
        )
        if sec_teams:
            print(f"  - Security manager teams: {len(sec_teams)}")

        # Print warnings (non-fatal)
        all_warnings = team_warnings
        if flat_teams:
            all_warnings.extend(team_xref_warnings)
        if all_warnings:
            print()
            print("Warnings:")
            for warning in all_warnings:
                print(f"  - {warning}")

        if members:
            print(f"  - Members: {len(members)}")
        print(f"  - Rulesets (repo-scoped): {len(repo_rulesets)}")
        if org_rulesets:
            print(f"  - Rulesets (org-scoped): {len(org_rulesets)}")
        sys.exit(0)


if __name__ == "__main__":
    main()
