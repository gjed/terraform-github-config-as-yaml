"""Tests for review_request_delegation validation in validate-config.py.

The GitHub provider only accepts ROUND_ROBIN and LOAD_BALANCE for the
delegation algorithm and rejects any other casing outright. The validator
compares case-insensitively so configurations written against the earlier
lowercase documentation keep validating, since the module upper-cases the
value before handing it to the provider.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

validate_config = importlib.import_module("validate-config")
validate_teams = validate_config.validate_teams


def _team(delegation) -> dict:
    return {
        "eng": {
            "description": "Engineering",
            "privacy": "closed",
            "review_request_delegation": delegation,
        }
    }


class TestDelegationAlgorithm:
    """Algorithm values accepted by validate_teams()."""

    def test_uppercase_round_robin_accepted(self):
        errors, _ = validate_teams(_team({"algorithm": "ROUND_ROBIN"}))
        assert errors == []

    def test_uppercase_load_balance_accepted(self):
        errors, _ = validate_teams(_team({"algorithm": "LOAD_BALANCE"}))
        assert errors == []

    def test_lowercase_still_accepted(self):
        """Pre-existing lowercase configs are normalised by the module."""
        errors, _ = validate_teams(_team({"algorithm": "round_robin"}))
        assert errors == []

    def test_mixed_case_accepted(self):
        errors, _ = validate_teams(_team({"algorithm": "Round_Robin"}))
        assert errors == []

    def test_unknown_algorithm_rejected(self):
        errors, _ = validate_teams(_team({"algorithm": "random"}))
        assert len(errors) == 1
        assert "invalid delegation algorithm" in errors[0]

    def test_error_message_lists_provider_casing(self):
        """The suggestion must match what the provider actually accepts."""
        errors, _ = validate_teams(_team({"algorithm": "random"}))
        assert "ROUND_ROBIN" in errors[0]
        assert "LOAD_BALANCE" in errors[0]

    def test_non_string_algorithm_rejected(self):
        errors, _ = validate_teams(_team({"algorithm": 5}))
        assert len(errors) == 1
        assert "must be a string" in errors[0]

    def test_omitted_algorithm_accepted(self):
        errors, _ = validate_teams(_team({"member_count": 2}))
        assert errors == []


class TestDelegationMemberCount:
    """member_count bounds."""

    def test_positive_accepted(self):
        errors, _ = validate_teams(_team({"member_count": 3}))
        assert errors == []

    def test_zero_rejected(self):
        errors, _ = validate_teams(_team({"member_count": 0}))
        assert len(errors) == 1
        assert "greater than 0" in errors[0]

    def test_negative_rejected(self):
        errors, _ = validate_teams(_team({"member_count": -1}))
        assert len(errors) == 1
        assert "greater than 0" in errors[0]


class TestDelegationShape:
    """Whole-block handling."""

    def test_null_delegation_accepted(self):
        errors, _ = validate_teams(_team(None))
        assert errors == []

    def test_non_mapping_rejected(self):
        errors, _ = validate_teams(_team("round_robin"))
        assert len(errors) == 1
        assert "must be a mapping" in errors[0]
