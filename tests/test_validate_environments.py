"""Tests for `environments:` validation in validate-config.py.

Terraform enforces the mutual-exclusion and wait_timer rules in preconditions and the
secret rules at plan time; these tests keep the offline validator aligned with it.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

validate_config = importlib.import_module("validate-config")
validate_environment = validate_config.validate_environment
validate_all_environment_blocks = validate_config.validate_all_environment_blocks
validate_environments_tier = validate_config.validate_environments_tier
VALID_GROUP_KEYS = validate_config.VALID_GROUP_KEYS


def _errors(env) -> list[str]:
    return validate_environment("repository 'r'", "production", env)


class TestValidEnvironments:
    def test_full_environment_has_no_errors(self):
        env = {
            "wait_timer": 10,
            "can_admins_bypass": False,
            "prevent_self_review": True,
            "reviewers": {"users": ["octocat"], "teams": ["platform"]},
            "deployment_branch_policy": {
                "custom_branch_policies": True,
                "branch_patterns": ["main", "release/*"],
                "tag_patterns": ["v*"],
            },
            "secrets": {"E2E_GITHUB_TOKEN": {"value": "env:E2E_GITHUB_TOKEN"}},
            "variables": {"FOO": {"value": "bar"}, "RETRIES": {"value": 3}},
        }
        assert _errors(env) == []

    def test_protected_branches_only(self):
        assert _errors({"deployment_branch_policy": {"protected_branches": True}}) == []

    @pytest.mark.parametrize("env", [None, {}])
    def test_empty_environment_is_valid(self, env):
        assert _errors(env) == []

    def test_null_properties_are_valid(self):
        env = {
            "wait_timer": None,
            "reviewers": None,
            "deployment_branch_policy": None,
            "secrets": None,
            "variables": None,
        }
        assert _errors(env) == []

    def test_environments_is_a_valid_group_key(self):
        assert "environments" in VALID_GROUP_KEYS


class TestBranchPolicy:
    def test_protected_and_custom_are_mutually_exclusive(self):
        errors = _errors(
            {
                "deployment_branch_policy": {
                    "protected_branches": True,
                    "custom_branch_policies": True,
                }
            }
        )
        assert len(errors) == 1
        assert "mutually exclusive" in errors[0]
        assert "environment 'production'" in errors[0]

    def test_both_false_is_not_an_exclusion_error(self):
        policy = {"protected_branches": False, "custom_branch_policies": False}
        assert _errors({"deployment_branch_policy": policy}) == []

    @pytest.mark.parametrize("key", ["branch_patterns", "tag_patterns"])
    def test_patterns_require_custom_branch_policies(self, key):
        errors = _errors({"deployment_branch_policy": {key: ["main"]}})
        assert len(errors) == 1
        assert "custom_branch_policies: true" in errors[0]

    def test_patterns_with_protected_branches_are_rejected(self):
        errors = _errors(
            {
                "deployment_branch_policy": {
                    "protected_branches": True,
                    "branch_patterns": ["main"],
                }
            }
        )
        assert len(errors) == 1

    def test_unknown_policy_key(self):
        errors = _errors({"deployment_branch_policy": {"branches": ["main"]}})
        assert len(errors) == 1
        assert "unknown key 'branches'" in errors[0]

    def test_flags_must_be_booleans(self):
        errors = _errors({"deployment_branch_policy": {"protected_branches": "yes"}})
        assert len(errors) == 1
        assert "must be a boolean" in errors[0]

    def test_patterns_must_be_a_list_of_strings(self):
        policy = {"custom_branch_policies": True, "branch_patterns": "main"}
        assert len(_errors({"deployment_branch_policy": policy})) == 1


class TestEnvironmentKeys:
    def test_unknown_key(self):
        errors = _errors({"wait_time": 5})
        assert len(errors) == 1
        assert "unknown key 'wait_time'" in errors[0]

    def test_environment_must_be_a_mapping(self):
        assert len(_errors(["a"])) == 1

    @pytest.mark.parametrize("value", [-1, 43201, "5", True, 1.5])
    def test_invalid_wait_timer(self, value):
        errors = _errors({"wait_timer": value})
        assert len(errors) == 1
        assert "wait_timer" in errors[0]

    @pytest.mark.parametrize("value", [0, 43200])
    def test_wait_timer_bounds(self, value):
        assert _errors({"wait_timer": value}) == []

    @pytest.mark.parametrize("key", ["can_admins_bypass", "prevent_self_review"])
    def test_booleans(self, key):
        assert len(_errors({key: "true"})) == 1


class TestReviewers:
    def test_unknown_reviewer_key(self):
        errors = _errors({"reviewers": {"groups": ["a"]}})
        assert len(errors) == 1
        assert "reviewers.groups" in errors[0]

    def test_reviewers_must_be_a_mapping(self):
        assert len(_errors({"reviewers": ["octocat"]})) == 1

    def test_logins_must_be_strings(self):
        assert len(_errors({"reviewers": {"users": [1234]}})) == 1

    def test_six_reviewers_are_allowed(self):
        reviewers = {"users": ["a", "b", "c"], "teams": ["d", "e", "f"]}
        assert _errors({"reviewers": reviewers}) == []

    def test_more_than_six_reviewers_are_rejected(self):
        reviewers = {"users": ["a", "b", "c", "d"], "teams": ["e", "f", "g"]}
        errors = _errors({"reviewers": reviewers})
        assert len(errors) == 1
        assert "at most 6" in errors[0]


class TestSecretsAndVariables:
    @pytest.mark.parametrize("name", ["lowercase", "GITHUB_TOKEN", "BAD-NAME"])
    def test_invalid_secret_names(self, name):
        errors = _errors({"secrets": {name: {"value": "env:OK"}}})
        assert len(errors) == 1
        assert "must match" in errors[0]

    @pytest.mark.parametrize("name", ["lowercase", "GITHUB_ENV"])
    def test_invalid_variable_names(self, name):
        assert len(_errors({"variables": {name: {"value": "x"}}})) == 1

    def test_secret_value_must_be_env_reference(self):
        literal = "hunter2-literal-secret"  # pragma: allowlist secret
        errors = _errors({"secrets": {"TOKEN": {"value": literal}}})
        assert len(errors) == 1
        assert "env:VAR_NAME" in errors[0]
        assert literal not in errors[0]

    def test_secret_without_value(self):
        assert len(_errors({"secrets": {"TOKEN": {}}})) == 1

    def test_unknown_secret_key(self):
        errors = _errors({"secrets": {"TOKEN": {"value": "env:T", "visibility": "all"}}})
        assert len(errors) == 1
        assert "unknown key 'visibility'" in errors[0]

    def test_variable_value_must_be_scalar(self):
        assert len(_errors({"variables": {"FOO": {"value": ["a"]}}})) == 1

    def test_secrets_must_be_a_mapping(self):
        assert len(_errors({"secrets": ["TOKEN"]})) == 1


class TestEnvironmentBlocks:
    def test_validates_groups_and_repositories(self):
        groups = {"g": {"environments": {"staging": {"wait_time": 1}}}}
        repos = {"r": {"environments": {"production": {"wait_timer": -1}}}}
        errors = validate_all_environment_blocks(groups, repos)
        assert len(errors) == 2
        assert "group 'g'" in errors[0]
        assert "repository 'r'" in errors[1]

    def test_environments_must_be_a_mapping(self):
        errors = validate_all_environment_blocks({}, {"r": {"environments": ["prod"]}})
        assert len(errors) == 1

    def test_no_environments_is_valid(self):
        assert validate_all_environment_blocks({"g": {}}, {"r": {"groups": ["g"]}}) == []

    def test_non_string_environment_name(self):
        errors = validate_all_environment_blocks({}, {"r": {"environments": {1: {}}}})
        assert len(errors) == 1


class TestEnvironmentsTier:
    GROUPS = {
        "with-env": {"environments": {"production": {}}},
        "public": {"visibility": "public"},
        "plain": {},
    }

    def test_free_tier_private_repo_warns(self):
        repos = {"app": {"groups": ["with-env"]}}
        warnings = validate_environments_tier(repos, self.GROUPS, "free")
        assert len(warnings) == 1
        assert "app" in warnings[0]
        assert "skipped" in warnings[0]

    def test_free_tier_repo_level_environments_warn(self):
        repos = {"app": {"groups": ["plain"], "environments": {"production": {}}}}
        assert len(validate_environments_tier(repos, self.GROUPS, "free")) == 1

    def test_public_repo_does_not_warn(self):
        repos = {"app": {"groups": ["with-env", "public"]}}
        assert validate_environments_tier(repos, self.GROUPS, "free") == []

    def test_repo_visibility_overrides_group(self):
        repos = {"app": {"groups": ["with-env", "public"], "visibility": "private"}}
        assert len(validate_environments_tier(repos, self.GROUPS, "free")) == 1

    def test_repo_without_environments_does_not_warn(self):
        repos = {"app": {"groups": ["plain"]}}
        assert validate_environments_tier(repos, self.GROUPS, "free") == []

    @pytest.mark.parametrize("tier", ["pro", "team", "enterprise"])
    def test_paid_tiers_do_not_warn(self, tier):
        repos = {"app": {"groups": ["with-env"]}}
        assert validate_environments_tier(repos, self.GROUPS, tier) == []
