"""Tests for branch protection validation in validate-config.py."""

from __future__ import annotations

import sys
from pathlib import Path

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Import after path manipulation — the module is a script, not a package
import importlib

validate_config = importlib.import_module("validate-config")
validate_branch_protections = validate_config.validate_branch_protections


class TestValidateBranchProtections:
    """Test validate_branch_protections()."""

    def test_empty_config_returns_no_errors(self):
        errors = validate_branch_protections({})
        assert errors == []

    def test_valid_minimal_protection(self):
        """Only 'pattern' is required."""
        config = {
            "main-protection": {
                "pattern": "main",
            }
        }
        errors = validate_branch_protections(config)
        assert errors == []

    def test_valid_full_protection(self):
        """All optional fields present and valid."""
        config = {
            "strict-protection": {
                "pattern": "main",
                "enforce_admins": True,
                "allows_deletions": False,
                "allows_force_pushes": False,
                "lock_branch": False,
                "require_conversation_resolution": True,
                "require_signed_commits": True,
                "required_linear_history": True,
                "required_pull_request_reviews": {
                    "required_approving_review_count": 2,
                    "dismiss_stale_reviews": True,
                    "require_code_owner_reviews": True,
                    "require_last_push_approval": True,
                    "restrict_dismissals": False,
                },
                "required_status_checks": {
                    "strict": True,
                    "contexts": ["ci/build", "ci/test"],
                },
                "restrict_pushes": {
                    "blocks_creations": False,
                },
            }
        }
        errors = validate_branch_protections(config)
        assert errors == []

    def test_non_dict_entry_is_error(self):
        config = {"bad": "not-a-dict"}
        errors = validate_branch_protections(config)
        assert len(errors) == 1
        assert "must be a mapping" in errors[0]
        assert "'bad'" in errors[0]

    def test_missing_pattern_is_error(self):
        config = {"no-pattern": {"enforce_admins": True}}
        errors = validate_branch_protections(config)
        assert len(errors) == 1
        assert "missing required field 'pattern'" in errors[0]
        assert "'no-pattern'" in errors[0]

    def test_non_string_pattern_is_error(self):
        config = {"bad-pattern": {"pattern": 123}}
        errors = validate_branch_protections(config)
        assert len(errors) == 1
        assert "pattern" in errors[0]
        assert "must be a string" in errors[0]

    def test_boolean_fields_reject_non_bool(self):
        config = {
            "bad-bools": {
                "pattern": "main",
                "enforce_admins": "yes",
            }
        }
        errors = validate_branch_protections(config)
        assert len(errors) == 1
        assert "enforce_admins" in errors[0]
        assert "must be a boolean" in errors[0]

    def test_required_pull_request_reviews_non_dict_is_error(self):
        config = {
            "bad-pr": {
                "pattern": "main",
                "required_pull_request_reviews": "invalid",
            }
        }
        errors = validate_branch_protections(config)
        assert len(errors) == 1
        assert "required_pull_request_reviews" in errors[0]
        assert "must be a mapping" in errors[0]

    def test_required_pull_request_reviews_bad_count(self):
        config = {
            "bad-count": {
                "pattern": "main",
                "required_pull_request_reviews": {
                    "required_approving_review_count": "two",
                },
            }
        }
        errors = validate_branch_protections(config)
        assert len(errors) == 1
        assert "required_approving_review_count" in errors[0]
        assert "integer" in errors[0]

    def test_required_pull_request_reviews_negative_count(self):
        config = {
            "neg-count": {
                "pattern": "main",
                "required_pull_request_reviews": {
                    "required_approving_review_count": -1,
                },
            }
        }
        errors = validate_branch_protections(config)
        assert len(errors) == 1
        assert "non-negative" in errors[0]

    def test_required_status_checks_non_dict_is_error(self):
        config = {
            "bad-sc": {
                "pattern": "main",
                "required_status_checks": "invalid",
            }
        }
        errors = validate_branch_protections(config)
        assert len(errors) == 1
        assert "required_status_checks" in errors[0]
        assert "must be a mapping" in errors[0]

    def test_required_status_checks_contexts_must_be_list(self):
        config = {
            "bad-ctx": {
                "pattern": "main",
                "required_status_checks": {
                    "contexts": "ci/build",
                },
            }
        }
        errors = validate_branch_protections(config)
        assert len(errors) == 1
        assert "contexts" in errors[0]
        assert "list" in errors[0]

    def test_restrict_pushes_non_dict_is_error(self):
        config = {
            "bad-rp": {
                "pattern": "main",
                "restrict_pushes": "invalid",
            }
        }
        errors = validate_branch_protections(config)
        assert len(errors) == 1
        assert "restrict_pushes" in errors[0]
        assert "must be a mapping" in errors[0]

    def test_multiple_protections_validated_independently(self):
        config = {
            "good": {"pattern": "main"},
            "bad": {"enforce_admins": True},  # missing pattern
        }
        errors = validate_branch_protections(config)
        assert len(errors) == 1
        assert "'bad'" in errors[0]


class TestBranchProtectionReferences:
    """Test validate_branch_protection_references()."""

    def test_no_references_no_errors(self):
        validate_refs = validate_config.validate_branch_protection_references
        errors = validate_refs(
            repos={"my-repo": {"description": "test", "groups": ["oss"]}},
            groups={"oss": {"visibility": "public"}},
            branch_protections={"main-protection": {"pattern": "main"}},
        )
        assert errors == []

    def test_valid_group_reference(self):
        validate_refs = validate_config.validate_branch_protection_references
        errors = validate_refs(
            repos={
                "my-repo": {"description": "test", "groups": ["oss"]},
            },
            groups={
                "oss": {
                    "visibility": "public",
                    "branch_protections": ["main-protection"],
                },
            },
            branch_protections={"main-protection": {"pattern": "main"}},
        )
        assert errors == []

    def test_invalid_group_reference(self):
        validate_refs = validate_config.validate_branch_protection_references
        errors = validate_refs(
            repos={
                "my-repo": {"description": "test", "groups": ["oss"]},
            },
            groups={
                "oss": {
                    "visibility": "public",
                    "branch_protections": ["nonexistent"],
                },
            },
            branch_protections={"main-protection": {"pattern": "main"}},
        )
        assert len(errors) == 1
        assert "nonexistent" in errors[0]
        assert "Group 'oss'" in errors[0]

    def test_valid_repo_reference(self):
        validate_refs = validate_config.validate_branch_protection_references
        errors = validate_refs(
            repos={
                "my-repo": {
                    "description": "test",
                    "groups": ["oss"],
                    "branch_protections": ["main-protection"],
                },
            },
            groups={"oss": {"visibility": "public"}},
            branch_protections={"main-protection": {"pattern": "main"}},
        )
        assert errors == []

    def test_invalid_repo_reference(self):
        validate_refs = validate_config.validate_branch_protection_references
        errors = validate_refs(
            repos={
                "my-repo": {
                    "description": "test",
                    "groups": ["oss"],
                    "branch_protections": ["nonexistent"],
                },
            },
            groups={"oss": {"visibility": "public"}},
            branch_protections={"main-protection": {"pattern": "main"}},
        )
        assert len(errors) == 1
        assert "nonexistent" in errors[0]
        assert "my-repo" in errors[0]

    def test_non_string_reference_is_error(self):
        validate_refs = validate_config.validate_branch_protection_references
        errors = validate_refs(
            repos={
                "my-repo": {
                    "description": "test",
                    "groups": ["oss"],
                    "branch_protections": [123],
                },
            },
            groups={"oss": {"visibility": "public"}},
            branch_protections={},
        )
        assert len(errors) == 1
        assert "must be a string" in errors[0]
