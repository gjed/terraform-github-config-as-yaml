"""Tests for validate_actions_tier_conflict() in validate-config.py.

Verified empirically against the live GitHub API: once an organization sets
allowed_actions=selected, GitHub unconditionally rejects any repository-level
PUT to actions/permissions/selected-actions with a 409 Conflict — even when
the repo's requested config is byte-identical to the org's. This is a
guaranteed apply-time failure, not a silent skip, so it is reported as an
error rather than a warning.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import importlib

validate_config = importlib.import_module("validate-config")
validate_actions_tier_conflict = validate_config.validate_actions_tier_conflict


ORG_SELECTED = {
    "allowed_actions": "selected",
    "allowed_actions_config": {"patterns_allowed": ["actions/checkout@*"]},
}

ORG_ALL = {"allowed_actions": "all"}


class TestNoOrgActionsConfig:
    def test_no_org_actions_returns_no_errors(self):
        repos = {"repo-a": {"actions": {"allowed_actions": "selected"}}}
        errors = validate_actions_tier_conflict(repos, {}, None)
        assert errors == []

    def test_org_allowed_actions_all_returns_no_errors(self):
        """Repo-level config is fine as long as the org isn't 'selected'."""
        repos = {"repo-a": {"actions": {"allowed_actions": "selected"}}}
        errors = validate_actions_tier_conflict(repos, {}, ORG_ALL)
        assert errors == []


class TestOrgSelectedWithRepoLevelActions:
    def test_repo_level_actions_block_flagged(self):
        repos = {"repo-a": {"actions": {"allowed_actions": "selected"}}}
        errors = validate_actions_tier_conflict(repos, {}, ORG_SELECTED)
        assert len(errors) == 1
        assert "repo-a" in errors[0]
        assert "409" in errors[0]

    def test_group_level_actions_block_flagged(self):
        """Inherited-from-group actions config also triggers the conflict."""
        repos = {"repo-a": {"groups": ["restricted"]}}
        groups = {"restricted": {"actions": {"allowed_actions": "selected"}}}
        errors = validate_actions_tier_conflict(repos, groups, ORG_SELECTED)
        assert len(errors) == 1
        assert "repo-a" in errors[0]

    def test_repo_with_no_actions_config_not_flagged(self):
        """No repo/group actions block means the repo inherits the org's list —
        verified empirically to succeed with no explicit resource needed."""
        repos = {"repo-a": {}}
        errors = validate_actions_tier_conflict(repos, {}, ORG_SELECTED)
        assert errors == []

    def test_identical_config_still_flagged(self):
        """GitHub rejects even a repo-level config identical to the org's —
        verified against the live API, not just a differing one."""
        repos = {"repo-a": {"actions": ORG_SELECTED}}
        errors = validate_actions_tier_conflict(repos, {}, ORG_SELECTED)
        assert len(errors) == 1

    def test_multiple_repos_all_flagged(self):
        repos = {
            "repo-a": {"actions": {"allowed_actions": "selected"}},
            "repo-b": {"actions": {"allowed_actions": "all"}},
            "repo-c": {},
        }
        errors = validate_actions_tier_conflict(repos, {}, ORG_SELECTED)
        assert len(errors) == 2
        joined = " ".join(errors)
        assert "repo-a" in joined
        assert "repo-b" in joined
        assert "repo-c" not in joined

    def test_repo_level_overrides_group_level_for_resolution(self):
        """Repo key wins in resolution, but either source still has an actions
        block present, so the conflict is still flagged."""
        repos = {"repo-a": {"groups": ["base"], "actions": {"enabled": False}}}
        groups = {"base": {"actions": {"allowed_actions": "selected"}}}
        errors = validate_actions_tier_conflict(repos, groups, ORG_SELECTED)
        assert len(errors) == 1

    def test_non_dict_repo_config_skipped(self):
        repos = {"repo-a": "not-a-dict"}
        errors = validate_actions_tier_conflict(repos, {}, ORG_SELECTED)
        assert errors == []
