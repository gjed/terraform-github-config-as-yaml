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

VALID_VISIBILITIES = ["public", "private", "internal"]
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


def flatten_teams(teams: dict, depth: int = 0, parent: str = None) -> list[dict]:
    """Recursively flatten nested team definitions."""
    result = []
    for slug, config in teams.items():
        if not isinstance(config, dict):
            continue
        result.append(
            {
                "slug": slug,
                "config": config,
                "depth": depth,
                "parent": parent,
            }
        )
        # Recurse into nested teams
        nested = config.get("teams", {})
        if isinstance(nested, dict) and nested:
            result.extend(flatten_teams(nested, depth + 1, slug))
    return result


def validate_teams(teams: dict) -> tuple[list[str], list[str]]:
    """Validate teams configuration. Returns (errors, warnings)."""
    errors = []
    warnings = []

    if not teams:
        return errors, warnings

    flat = flatten_teams(teams)

    # Check for duplicate slugs
    slugs = [t["slug"] for t in flat]
    seen = set()
    for slug in slugs:
        if slug in seen:
            errors.append(f"teams: Duplicate team slug '{slug}' found across hierarchy")
        seen.add(slug)

    # Check max nesting depth
    for team in flat:
        if team["depth"] > 2:
            errors.append(
                f"teams: Team '{team['slug']}' exceeds maximum nesting depth of 3 levels "
                f"(depth {team['depth'] + 1})"
            )

    # Validate each team's fields
    _slug_re = re.compile(r"^[a-z0-9][a-z0-9\-]*$")
    for team in flat:
        slug = team["slug"]
        config = team["config"]

        # Validate slug characters (GitHub normalises slugs; mismatches cause confusing state)
        if not _slug_re.match(slug):
            errors.append(
                f"teams: Team slug '{slug}' contains invalid characters. "
                f"Use only lowercase letters, digits, and hyphens (e.g. 'platform-team')."
            )

        if "description" not in config:
            errors.append(f"teams: Team '{slug}' missing required field 'description'")

        privacy = config.get("privacy")
        if privacy and privacy not in VALID_TEAM_PRIVACIES:
            errors.append(
                f"teams: Team '{slug}' has invalid privacy '{privacy}'. "
                f"Valid values: {', '.join(VALID_TEAM_PRIVACIES)}"
            )

        # Validate no overlap between members and maintainers
        members = set(config.get("members", []))
        maintainers = set(config.get("maintainers", []))
        overlap = members & maintainers
        if overlap:
            errors.append(
                f"teams: Team '{slug}' has users in both members and maintainers: "
                f"{', '.join(sorted(overlap))}"
            )

        # Validate review_request_delegation
        # 'enabled' is optional (defaults to true); only validate algorithm when present
        delegation = config.get("review_request_delegation")
        if isinstance(delegation, dict):
            algorithm = delegation.get("algorithm")
            if algorithm and algorithm not in VALID_DELEGATION_ALGORITHMS:
                errors.append(
                    f"teams: Team '{slug}' has invalid delegation algorithm '{algorithm}'. "
                    f"Valid values: {', '.join(VALID_DELEGATION_ALGORITHMS)}"
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

        # Load teams (optional directory)
        if TEAM_DIR.exists():
            teams = load_yaml_directory(TEAM_DIR)
        else:
            teams = {}
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Validate each config type
    all_errors.extend(validate_config(config))
    all_errors.extend(validate_groups(groups))
    all_errors.extend(validate_rulesets(rulesets))
    all_errors.extend(validate_repositories(repos, groups, rulesets))

    # Flatten once; reused by validate_teams, cross-ref check, and summary output
    flat_teams = flatten_teams(teams) if teams else []

    team_errors, team_warnings = validate_teams(teams)
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

        sys.exit(0)


if __name__ == "__main__":
    main()
