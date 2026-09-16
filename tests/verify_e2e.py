#!/usr/bin/env python3
"""
Post-apply verification script for the e2e test fixture.

Reads terraform output -json from a file argument, connects to the GitHub API
using GITHUB_TOKEN, and asserts that provisioned state matches declared config.

Usage:
    terraform output -json > /tmp/e2e_outputs.json
    python3 tests/verify_e2e.py /tmp/e2e_outputs.json

Exit codes:
    0  All assertions passed
    1  One or more assertions failed (or usage error)
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any

try:
    from github import Github, GithubException
except ImportError:
    print("ERROR: PyGithub is required. Install with: pip install PyGithub")
    sys.exit(1)


# ── Result tracking ──────────────────────────────────────────────────────────


@dataclass
class CheckResult:
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def ok(self, msg: str) -> None:
        self.passed.append(msg)
        print(f"  ✓ {msg}")

    def fail(self, msg: str) -> None:
        self.failed.append(msg)
        print(f"  ✗ {msg}")

    def assert_eq(self, label: str, expected: Any, actual: Any) -> None:
        if expected == actual:
            self.ok(f"{label}: {actual!r}")
        else:
            self.fail(f"{label}: expected {expected!r}, got {actual!r}")

    def assert_contains(self, label: str, container: Any, item: Any) -> None:
        if item in container:
            self.ok(f"{label}: {item!r} found")
        else:
            self.fail(f"{label}: {item!r} not found in {container!r}")

    def assert_not_none(self, label: str, value: Any) -> None:
        if value is not None:
            self.ok(f"{label}: non-null ✓")
        else:
            self.fail(f"{label}: expected non-null, got null")

    def assert_is_none(self, label: str, value: Any) -> None:
        if value is None:
            self.ok(f"{label}: null ✓")
        else:
            self.fail(f"{label}: expected null, got {value!r}")


# ── Check functions ───────────────────────────────────────────────────────────


def verify_repositories(result: CheckResult, outputs: dict, gh_org) -> None:
    """For each repo in outputs, assert it exists on GitHub with correct visibility."""
    print("\n## Repository checks")
    repos_output = outputs.get("repositories", {}).get("value", {})
    if not repos_output:
        result.fail("repositories output is empty — no repos to verify")
        return

    for repo_name, repo_info in repos_output.items():
        expected_visibility = repo_info.get("visibility")
        try:
            gh_repo = gh_org.get_repo(repo_name)
            # GitHub API returns "public"/"private" which matches Terraform output
            actual_visibility = "private" if gh_repo.private else "public"
            result.assert_eq(
                f"repo {repo_name} visibility",
                expected_visibility,
                actual_visibility,
            )
        except GithubException as e:
            result.fail(f"repo {repo_name}: GitHub API error — {e}")


def verify_teams(result: CheckResult, outputs: dict, gh_org) -> None:
    """For each team in managed_teams output, assert it exists on GitHub by slug."""
    print("\n## Team checks")
    teams_output = outputs.get("managed_teams", {}).get("value", {})
    if not teams_output:
        result.ok(
            "managed_teams output is empty — no teams to verify (is_organization may be false)"
        )
        return

    for slug in teams_output:
        try:
            gh_org.get_team_by_slug(slug)
            result.ok(f"team {slug!r} exists")
        except GithubException as e:
            result.fail(f"team {slug!r}: GitHub API error — {e}")


def verify_subscription_warnings(result: CheckResult, outputs: dict) -> None:
    """Assert subscription_warnings is non-null on free tier with private rulesets."""
    print("\n## Subscription warnings check")
    warnings = outputs.get("subscription_warnings", {}).get("value")
    result.assert_not_none("subscription_warnings", warnings)
    if warnings is not None:
        repos = warnings.get("repos", [])
        result.assert_contains(
            "subscription_warnings.repos contains e2e-internal-private",
            repos,
            "e2e-internal-private",
        )


def verify_skipped_branch_protections(result: CheckResult, outputs: dict) -> None:
    """Assert branch protections are skipped for private repos on the free tier.

    GitHub does not offer protected branches on private repositories at the free
    tier, so the module filters them out and reports the affected repositories.
    """
    print("\n## Skipped branch protections check")
    tier = outputs.get("subscription_tier", {}).get("value")
    skipped = outputs.get("skipped_branch_protections", {}).get("value")

    if tier != "free":
        result.assert_is_none(
            f"skipped_branch_protections on {tier!r} tier", skipped
        )
        return

    result.assert_not_none("skipped_branch_protections", skipped)
    if skipped is None:
        return

    repos = skipped.get("repos", [])
    # Both inherit branch_protections from the private internal-e2e group.
    for expected in ("e2e-internal-private", "e2e-multi-group"):
        result.assert_contains(
            f"skipped_branch_protections.repos contains {expected}", repos, expected
        )
    # e2e-full-featured is public, so its protections are applied, not skipped.
    if "e2e-full-featured" in repos:
        result.fail(
            "skipped_branch_protections.repos contains e2e-full-featured, "
            "but it is public and its protections should be applied"
        )
    else:
        result.ok("skipped_branch_protections excludes public e2e-full-featured")


def verify_branch_protection_state(result: CheckResult, outputs: dict, gh_org) -> None:
    """Assert live branch protection state matches the tier gating decision.

    The public repo must actually carry its protection on GitHub; the private
    repos listed as skipped must not.
    """
    print("\n## Branch protection state check")
    tier = outputs.get("subscription_tier", {}).get("value")
    skipped_output = outputs.get("skipped_branch_protections", {}).get("value") or {}
    skipped_repos = set(skipped_output.get("repos", []))

    def protection_state(repo_name: str) -> str | None:
        """Return 'protected', 'unprotected', 'no-branch', or None on API error."""
        try:
            gh_repo = gh_org.get_repo(repo_name)
        except GithubException as e:
            result.fail(f"repo {repo_name}: GitHub API error — {e}")
            return None
        try:
            branch = gh_repo.get_branch("main")
        except GithubException:
            # An empty repository has no default branch yet, so there is nothing
            # to protect. Not a failure of the gating logic.
            return "no-branch"
        return "protected" if branch.protected else "unprotected"

    # Public repo with branch_protections: must be protected on a free-tier org.
    state = protection_state("e2e-full-featured")
    if state == "no-branch":
        result.ok("e2e-full-featured: no default branch yet — protection not asserted")
    elif state is not None:
        result.assert_eq("e2e-full-featured branch 'main'", "protected", state)

    # Private repos reported as skipped must not be protected.
    for repo_name in sorted(skipped_repos):
        state = protection_state(repo_name)
        if state == "no-branch":
            result.ok(f"{repo_name}: no default branch yet — skip confirmed vacuously")
        elif state is not None:
            result.assert_eq(
                f"{repo_name} branch 'main' (skipped on {tier!r} tier)",
                "unprotected",
                state,
            )


def verify_vulnerability_alerts(result: CheckResult, outputs: dict, gh_org) -> None:
    """Assert Dependabot vulnerability alerts are enabled where configured.

    Covers github_repository_vulnerability_alerts, which replaced the deprecated
    inline argument and is otherwise unverified by this fixture.
    """
    print("\n## Vulnerability alerts check")
    repos = outputs.get("repositories", {}).get("value", {})
    # Every e2e repo inherits vulnerability_alerts: true from oss-e2e or internal-e2e.
    for repo_name in sorted(repos):
        try:
            gh_repo = gh_org.get_repo(repo_name)
            enabled = gh_repo.get_vulnerability_alert()
        except GithubException as e:
            result.fail(f"repo {repo_name} vulnerability alerts: GitHub API error — {e}")
            continue
        result.assert_eq(f"{repo_name} vulnerability alerts", True, enabled)


def verify_skipped_org_rulesets(result: CheckResult, outputs: dict) -> None:
    """Assert skipped_org_rulesets is non-null on free/pro tier."""
    print("\n## Skipped org rulesets check")
    skipped = outputs.get("skipped_org_rulesets", {}).get("value")
    result.assert_not_none("skipped_org_rulesets", skipped)
    if skipped is not None:
        rulesets = skipped.get("rulesets", [])
        result.assert_contains(
            "skipped_org_rulesets.rulesets contains e2e-org-protection",
            rulesets,
            "e2e-org-protection",
        )


def verify_org_webhooks(result: CheckResult, outputs: dict) -> None:
    """Assert e2e-org-webhook key present in org_webhooks output."""
    print("\n## Org webhook check")
    webhooks = outputs.get("org_webhooks", {}).get("value")
    if webhooks is None:
        result.fail("org_webhooks output is null")
        return
    result.assert_contains(
        "org_webhooks contains e2e-org-webhook", webhooks, "e2e-org-webhook"
    )


def verify_no_duplicate_warnings(result: CheckResult, outputs: dict) -> None:
    """Assert duplicate_key_warnings output is null (no duplicate config keys)."""
    print("\n## Duplicate key warnings check")
    warnings = outputs.get("duplicate_key_warnings", {}).get("value")
    result.assert_is_none("duplicate_key_warnings", warnings)


def verify_partitioned_repo_loaded(result: CheckResult, outputs: dict) -> None:
    """Assert the subdirectory-defined e2e-partitioned-repo is loaded."""
    print("\n## Subdirectory loading check")
    repos = outputs.get("repositories", {}).get("value", {})
    result.assert_contains(
        "repositories contains e2e-partitioned-repo",
        repos,
        "e2e-partitioned-repo",
    )


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <terraform-outputs.json>")
        sys.exit(1)

    outputs_path = sys.argv[1]

    # Load terraform outputs JSON
    try:
        with open(outputs_path) as f:
            outputs = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: Could not read outputs file {outputs_path!r}: {e}")
        sys.exit(1)

    # Check GITHUB_TOKEN
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable is required.")
        print(
            "Set it to a fine-grained PAT scoped to the test org. See "
            "tests/e2e/README.md for the exact permission set."
        )
        sys.exit(1)

    # Determine org name from outputs
    org_name = outputs.get("organization", {}).get("value")
    if not org_name:
        print("ERROR: 'organization' output not found in Terraform outputs.")
        sys.exit(1)

    print(f"Verifying e2e fixture for org: {org_name!r}")
    print(f"Reading outputs from: {outputs_path!r}")

    # Connect to GitHub API
    gh = Github(token)
    try:
        gh_org = gh.get_organization(org_name)
    except GithubException as e:
        print(f"ERROR: Could not access GitHub org {org_name!r}: {e}")
        sys.exit(1)

    result = CheckResult()

    # Run all checks
    verify_repositories(result, outputs, gh_org)
    verify_teams(result, outputs, gh_org)
    verify_subscription_warnings(result, outputs)
    verify_skipped_branch_protections(result, outputs)
    verify_branch_protection_state(result, outputs, gh_org)
    verify_vulnerability_alerts(result, outputs, gh_org)
    verify_skipped_org_rulesets(result, outputs)
    verify_org_webhooks(result, outputs)
    verify_no_duplicate_warnings(result, outputs)
    verify_partitioned_repo_loaded(result, outputs)

    # Summary
    total = len(result.passed) + len(result.failed)
    print(f"\n{'=' * 60}")
    print(
        f"Results: {len(result.passed)} passed, {len(result.failed)} failed (total: {total})"
    )

    if result.failed:
        print("\nFailed checks:")
        for msg in result.failed:
            print(f"  ✗ {msg}")
        sys.exit(1)
    else:
        print("All checks passed! ✓")
        sys.exit(0)


if __name__ == "__main__":
    main()
