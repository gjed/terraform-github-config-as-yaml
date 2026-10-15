"""Tests for required_reviewers validation in validate-config.py.

required_reviewers is a parameter of the pull_request rule. Each entry names a
reviewer team by exactly one of slug or id, a file_patterns list and a
minimum_approvals count. Slug existence is checked by Terraform, not here.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

validate_config = importlib.import_module("validate-config")
validate_rulesets = validate_config.validate_rulesets


def _entry(**overrides) -> dict:
    entry = {
        "reviewer": {"slug": "security-team"},
        "file_patterns": ["*.tf"],
        "minimum_approvals": 1,
    }
    entry.update(overrides)
    return entry


def _ruleset(required_reviewers, scope=None) -> dict:
    ruleset = {
        "target": "branch",
        "enforcement": "active",
        "conditions": {},
        "rules": [
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 1,
                    "required_reviewers": required_reviewers,
                },
            }
        ],
    }
    if scope is not None:
        ruleset["scope"] = scope
    return {"protect": ruleset}


def _errors(required_reviewers, scope=None) -> list[str]:
    return validate_rulesets(_ruleset(required_reviewers, scope))


class TestReviewerIdentity:
    """Exactly one of slug / id must identify the reviewer."""

    def test_valid_slug_accepted(self):
        assert _errors([_entry()]) == []

    def test_valid_id_accepted(self):
        assert _errors([_entry(reviewer={"id": 1234567})]) == []

    def test_valid_id_with_type_team_accepted(self):
        assert _errors([_entry(reviewer={"id": 1234567, "type": "Team"})]) == []

    def test_both_slug_and_id_rejected(self):
        errors = _errors([_entry(reviewer={"slug": "security-team", "id": 1234567})])
        assert len(errors) == 1
        assert "exactly one of 'slug' or 'id'" in errors[0]

    def test_neither_slug_nor_id_rejected(self):
        errors = _errors([_entry(reviewer={"type": "Team"})])
        assert len(errors) == 1
        assert "exactly one of 'slug' or 'id'" in errors[0]

    def test_reviewer_not_mapping_rejected(self):
        errors = _errors([_entry(reviewer="security-team")])
        assert len(errors) == 1
        assert "required_reviewers[0].reviewer' must be a mapping" in errors[0]

    def test_invalid_slug_rejected(self):
        errors = _errors([_entry(reviewer={"slug": "Security Team"})])
        assert len(errors) == 1
        assert "valid team slug" in errors[0]

    def test_non_string_slug_rejected(self):
        errors = _errors([_entry(reviewer={"slug": 42})])
        assert len(errors) == 1
        assert "valid team slug" in errors[0]

    def test_zero_id_rejected(self):
        errors = _errors([_entry(reviewer={"id": 0})])
        assert len(errors) == 1
        assert "positive integer" in errors[0]

    def test_string_id_rejected(self):
        errors = _errors([_entry(reviewer={"id": "1234567"})])
        assert len(errors) == 1
        assert "positive integer" in errors[0]

    def test_bool_id_rejected(self):
        errors = _errors([_entry(reviewer={"id": True})])
        assert len(errors) == 1
        assert "positive integer" in errors[0]

    def test_bad_type_rejected(self):
        errors = _errors([_entry(reviewer={"slug": "security-team", "type": "User"})])
        assert len(errors) == 1
        assert "must be 'Team'" in errors[0]


class TestFilePatternsAndApprovals:
    """file_patterns and minimum_approvals shape and bounds."""

    def test_empty_file_patterns_rejected(self):
        errors = _errors([_entry(file_patterns=[])])
        assert len(errors) == 1
        assert "required_reviewers[0].file_patterns' must be a non-empty list" in errors[0]

    def test_file_patterns_with_empty_string_rejected(self):
        errors = _errors([_entry(file_patterns=["*.tf", ""])])
        assert len(errors) == 1
        assert "file_patterns" in errors[0]

    def test_file_patterns_not_list_rejected(self):
        errors = _errors([_entry(file_patterns="*.tf")])
        assert len(errors) == 1
        assert "file_patterns" in errors[0]

    def test_minimum_approvals_zero_accepted(self):
        assert _errors([_entry(minimum_approvals=0)]) == []

    def test_minimum_approvals_ten_accepted(self):
        assert _errors([_entry(minimum_approvals=10)]) == []

    def test_minimum_approvals_above_range_rejected(self):
        errors = _errors([_entry(minimum_approvals=11)])
        assert len(errors) == 1
        assert "between 0 and 10" in errors[0]

    def test_minimum_approvals_negative_rejected(self):
        errors = _errors([_entry(minimum_approvals=-1)])
        assert len(errors) == 1
        assert "between 0 and 10" in errors[0]

    def test_minimum_approvals_bool_rejected(self):
        errors = _errors([_entry(minimum_approvals=True)])
        assert len(errors) == 1
        assert "between 0 and 10" in errors[0]

    def test_minimum_approvals_missing_rejected(self):
        entry = _entry()
        del entry["minimum_approvals"]
        errors = _errors([entry])
        assert len(errors) == 1
        assert "minimum_approvals" in errors[0]


class TestListShape:
    """Whole-list handling."""

    def test_null_accepted(self):
        assert _errors(None) == []

    def test_empty_list_accepted(self):
        assert _errors([]) == []

    def test_fifteen_entries_accepted(self):
        assert _errors([_entry() for _ in range(15)]) == []

    def test_more_than_fifteen_entries_rejected(self):
        errors = _errors([_entry() for _ in range(16)])
        assert len(errors) == 1
        assert "at most 15 entries" in errors[0]

    def test_not_a_list_rejected(self):
        errors = _errors({"reviewer": {"slug": "security-team"}})
        assert len(errors) == 1
        assert "must be a list" in errors[0]

    def test_entry_not_mapping_rejected(self):
        errors = _errors(["security-team"])
        assert len(errors) == 1
        assert "must be a mapping" in errors[0]


class TestErrorMessages:
    """Messages name the ruleset and the offending field."""

    def test_message_names_ruleset_and_field(self):
        errors = _errors([_entry(minimum_approvals=11)])
        assert "Ruleset 'protect'" in errors[0]
        assert "required_reviewers[0].minimum_approvals" in errors[0]


class TestOrgScopedRulesets:
    """Organization rulesets go through the same validation."""

    def test_org_scoped_valid_accepted(self):
        assert _errors([_entry(reviewer={"id": 1234567})], scope="organization") == []

    def test_org_scoped_invalid_rejected(self):
        errors = _errors([_entry(file_patterns=[])], scope="organization")
        assert len(errors) == 1
        assert "Ruleset 'protect'" in errors[0]
        assert "file_patterns" in errors[0]
