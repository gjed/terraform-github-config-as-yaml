#!/usr/bin/env python3
"""
Validate YAML configuration files for GitHub organization management.

Usage:
    python scripts/validate-config.py
    python scripts/validate-config.py --strict
"""

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

VALID_VISIBILITIES = ["public", "private", "internal"]
VALID_MEMBERSHIP_ROLES = ["member", "admin"]
VALID_PERMISSIONS = ["pull", "triage", "push", "maintain", "admin"]
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


def validate_config(config: dict) -> list[str]:
    """Validate config.yml."""
    errors = []

    if "organization" not in config:
        errors.append("config.yml: Missing required field 'organization'")

    subscription = config.get("subscription", "free")
    if subscription not in ["free", "pro", "team", "enterprise"]:
        errors.append(f"config.yml: Invalid subscription '{subscription}'")

    return errors


def validate_groups(groups: dict) -> list[str]:
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

    return errors


def validate_repositories(repos: dict, groups: dict, rulesets: dict) -> list[str]:
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
                if ruleset_entry not in rulesets:
                    errors.append(
                        f"repositories: Repository '{repo_name}' references unknown ruleset '{ruleset_entry}'"
                    )
            elif isinstance(ruleset_entry, dict) and "template" in ruleset_entry:
                template_name = ruleset_entry["template"]
                if template_name not in rulesets:
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
            for rule in ruleset_config["rules"]:
                if "type" not in rule:
                    errors.append(
                        f"rulesets: Ruleset '{ruleset_name}' has rule without 'type'"
                    )
                elif rule["type"] not in VALID_RULE_TYPES:
                    errors.append(
                        f"rulesets: Ruleset '{ruleset_name}' has invalid rule type '{rule['type']}'"
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


def main():
    """Main validation entry point."""
    strict = "--strict" in sys.argv
    all_errors = []

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
            repos = load_yaml_directory(REPOSITORY_DIR)
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
        # Membership directory is optional
        members = load_yaml_directory(MEMBERSHIP_DIR) if MEMBERSHIP_DIR.exists() else {}
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Validate each config type
    all_errors.extend(validate_config(config))
    all_errors.extend(validate_groups(groups))
    all_errors.extend(validate_rulesets(rulesets))
    all_errors.extend(validate_repositories(repos, groups, rulesets))
    all_errors.extend(validate_membership(members))

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
        print(f"  - Groups: {len(groups)}")
        print(f"  - Repositories: {len(repos)}")
        print(f"  - Rulesets: {len(rulesets)}")
        print(f"  - Teams: {len(flat_teams)}")

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
        sys.exit(0)


if __name__ == "__main__":
    main()
