"""Tests for unknown group/repository key detection in validate-config.py."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

validate_config = importlib.import_module("validate-config")
validate_unknown_keys = validate_config.validate_unknown_keys
VALID_GROUP_KEYS = validate_config.VALID_GROUP_KEYS
VALID_REPOSITORY_KEYS = validate_config.VALID_REPOSITORY_KEYS


class TestValidateUnknownKeys:
    """Test validate_unknown_keys()."""

    def test_all_valid_group_keys_no_warnings(self):
        groups = {"g": {key: None for key in VALID_GROUP_KEYS}}
        assert validate_unknown_keys(groups, VALID_GROUP_KEYS, "Group", "groups") == []

    def test_all_valid_repository_keys_no_warnings(self):
        repos = {"r": {key: None for key in VALID_REPOSITORY_KEYS}}
        assert (
            validate_unknown_keys(repos, VALID_REPOSITORY_KEYS, "Repository", "repositories")
            == []
        )

    def test_unknown_group_key_warns(self):
        groups = {"oss": {"has_wiki": True, "has_wikis": True}}
        warnings = validate_unknown_keys(groups, VALID_GROUP_KEYS, "Group", "groups")
        assert len(warnings) == 1
        assert "Group 'oss'" in warnings[0]
        assert "has_wikis" in warnings[0]

    def test_unknown_repository_key_warns(self):
        repos = {"repo": {"description": "d", "groups": ["g"], "bogus": 1}}
        warnings = validate_unknown_keys(
            repos, VALID_REPOSITORY_KEYS, "Repository", "repositories"
        )
        assert len(warnings) == 1
        assert "Repository 'repo'" in warnings[0]
        assert "bogus" in warnings[0]

    def test_group_does_not_accept_repository_identity_keys(self):
        groups = {"g": {"description": "x"}}
        warnings = validate_unknown_keys(groups, VALID_GROUP_KEYS, "Group", "groups")
        assert len(warnings) == 1

    def test_require_linear_history_has_dedicated_message(self):
        groups = {"oss": {"require_linear_history": True}}
        warnings = validate_unknown_keys(groups, VALID_GROUP_KEYS, "Group", "groups")
        assert len(warnings) == 1
        assert "not a repository setting" in warnings[0]
        assert "required_linear_history" in warnings[0]

    def test_non_dict_entries_skipped(self):
        assert validate_unknown_keys({"g": None}, VALID_GROUP_KEYS, "Group", "groups") == []
