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


class TestResolveEffectiveVisibility:
    """Test resolve_effective_visibility()."""

    def test_defaults_to_private(self):
        resolve = validate_config.resolve_effective_visibility
        assert resolve({"groups": []}, {}) == "private"

    def test_inherits_from_group(self):
        resolve = validate_config.resolve_effective_visibility
        assert resolve({"groups": ["oss"]}, {"oss": {"visibility": "public"}}) == "public"

    def test_later_group_overrides_earlier(self):
        """Mirrors Terraform merge order: groups applied in order, later wins."""
        resolve = validate_config.resolve_effective_visibility
        groups = {
            "oss": {"visibility": "public"},
            "internal": {"visibility": "private"},
        }
        assert resolve({"groups": ["oss", "internal"]}, groups) == "private"

    def test_repo_level_overrides_group(self):
        resolve = validate_config.resolve_effective_visibility
        repo = {"groups": ["oss"], "visibility": "private"}
        assert resolve(repo, {"oss": {"visibility": "public"}}) == "private"

    def test_unknown_group_is_ignored(self):
        resolve = validate_config.resolve_effective_visibility
        assert resolve({"groups": ["missing"]}, {}) == "private"

    def test_missing_groups_key(self):
        resolve = validate_config.resolve_effective_visibility
        assert resolve({}, {}) == "private"


class TestValidateBranchProtectionTier:
    """Test validate_branch_protection_tier()."""

    def test_free_tier_private_repo_warns(self):
        validate_tier = validate_config.validate_branch_protection_tier
        warnings = validate_tier(
            repos={
                "my-repo": {
                    "description": "test",
                    "groups": ["internal"],
                    "branch_protections": ["main-protection"],
                },
            },
            groups={"internal": {"visibility": "private"}},
            subscription="free",
        )
        assert len(warnings) == 1
        assert "my-repo" in warnings[0]

    def test_free_tier_public_repo_no_warning(self):
        validate_tier = validate_config.validate_branch_protection_tier
        warnings = validate_tier(
            repos={
                "my-repo": {
                    "description": "test",
                    "groups": ["oss"],
                    "branch_protections": ["main-protection"],
                },
            },
            groups={"oss": {"visibility": "public"}},
            subscription="free",
        )
        assert warnings == []

    def test_paid_tier_private_repo_no_warning(self):
        validate_tier = validate_config.validate_branch_protection_tier
        for tier in ("pro", "team", "enterprise"):
            warnings = validate_tier(
                repos={
                    "my-repo": {
                        "description": "test",
                        "groups": ["internal"],
                        "branch_protections": ["main-protection"],
                    },
                },
                groups={"internal": {"visibility": "private"}},
                subscription=tier,
            )
            assert warnings == [], f"tier {tier} should not warn"

    def test_protections_inherited_from_group_are_detected(self):
        """Repo has no branch_protections of its own; the group supplies them."""
        validate_tier = validate_config.validate_branch_protection_tier
        warnings = validate_tier(
            repos={
                "my-repo": {"description": "test", "groups": ["internal"]},
            },
            groups={
                "internal": {
                    "visibility": "private",
                    "branch_protections": ["main-protection"],
                }
            },
            subscription="free",
        )
        assert len(warnings) == 1
        assert "my-repo" in warnings[0]

    def test_private_repo_without_protections_no_warning(self):
        validate_tier = validate_config.validate_branch_protection_tier
        warnings = validate_tier(
            repos={"my-repo": {"description": "test", "groups": ["internal"]}},
            groups={"internal": {"visibility": "private"}},
            subscription="free",
        )
        assert warnings == []

    def test_visibility_defaults_to_private_when_unset(self):
        """No visibility anywhere means private, which warns on free."""
        validate_tier = validate_config.validate_branch_protection_tier
        warnings = validate_tier(
            repos={
                "my-repo": {
                    "description": "test",
                    "groups": ["base"],
                    "branch_protections": ["main-protection"],
                },
            },
            groups={"base": {}},
            subscription="free",
        )
        assert len(warnings) == 1

    def test_repo_override_to_public_suppresses_warning(self):
        """Group says private, repo overrides to public — no warning."""
        validate_tier = validate_config.validate_branch_protection_tier
        warnings = validate_tier(
            repos={
                "my-repo": {
                    "description": "test",
                    "groups": ["internal"],
                    "visibility": "public",
                    "branch_protections": ["main-protection"],
                },
            },
            groups={"internal": {"visibility": "private"}},
            subscription="free",
        )
        assert warnings == []

    def test_non_dict_repo_config_is_skipped(self):
        validate_tier = validate_config.validate_branch_protection_tier
        warnings = validate_tier(
            repos={"my-repo": "not-a-dict"},
            groups={},
            subscription="free",
        )
        assert warnings == []

    def test_multiple_private_repos_each_warn(self):
        validate_tier = validate_config.validate_branch_protection_tier
        warnings = validate_tier(
            repos={
                "repo-a": {
                    "description": "a",
                    "groups": ["internal"],
                    "branch_protections": ["bp"],
                },
                "repo-b": {
                    "description": "b",
                    "groups": ["internal"],
                    "branch_protections": ["bp"],
                },
            },
            groups={"internal": {"visibility": "private"}},
            subscription="free",
        )
        assert len(warnings) == 2
