"""Tests for secrets and variables validation in validate-config.py.

Covers org-level config/secret/*.yml files and group/repository `secrets:` and
`variables:` blocks. Terraform enforces the same name and env: rules at plan time;
these tests keep the offline validator aligned with it.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

validate_config = importlib.import_module("validate-config")
load_secret_files = validate_config.load_secret_files
validate_org_secret_files = validate_config.validate_org_secret_files
validate_all_repo_secret_blocks = validate_config.validate_all_repo_secret_blocks
validate_secret_name = validate_config.validate_secret_name

REPOS = {"repo-a", "repo-b"}


def _org(data: dict) -> dict:
    return {"org.yml": data}


class TestSecretNames:
    @pytest.mark.parametrize("name", ["DEPLOY_TOKEN", "_PRIVATE", "A1", "X_Y_2"])
    def test_valid_names(self, name):
        assert validate_secret_name("label", name) == []

    @pytest.mark.parametrize(
        "name", ["deploy_token", "Mixed", "1LEADING", "GITHUB_ENV_NAME", "BAD-NAME", "X\n"]
    )
    def test_invalid_names(self, name):
        assert len(validate_secret_name("label", name)) == 1

    def test_non_string_name_is_invalid(self):
        assert validate_secret_name("label", 123) != []


class TestOrgSecretFiles:
    def test_valid_file_has_no_errors(self):
        data = {
            "actions_secrets": {
                "DEPLOY_TOKEN": {
                    "value": "env:DEPLOY_TOKEN",
                    "visibility": "selected",
                    "selected_repositories": ["repo-a"],
                }
            },
            "actions_variables": {"ENVIRONMENT": {"value": 3, "visibility": "all"}},
            "dependabot_secrets": {
                "REGISTRY_PASSWORD": {"value": "env:REG", "visibility": "private"}
            },
        }
        errors, warnings = validate_org_secret_files(_org(data), REPOS)
        assert errors == []
        assert warnings == []

    def test_unknown_top_level_key_is_error(self):
        errors, _ = validate_org_secret_files(
            _org({"actions_secret": {"X": {"value": "env:X", "visibility": "all"}}}), REPOS
        )
        assert any("unknown key 'actions_secret'" in e for e in errors)

    def test_unknown_entry_key_is_error(self):
        data = {"actions_secrets": {"X": {"value": "env:X", "visibility": "all", "scope": 1}}}
        errors, _ = validate_org_secret_files(_org(data), REPOS)
        assert any("unknown key 'scope'" in e for e in errors)

    def test_lowercase_name_is_error(self):
        data = {"actions_secrets": {"deploy_token": {"value": "env:X", "visibility": "all"}}}
        errors, _ = validate_org_secret_files(_org(data), REPOS)
        assert any("'deploy_token'" in e for e in errors)

    def test_github_prefix_variable_is_error(self):
        data = {"actions_variables": {"GITHUB_ENV_NAME": {"value": "x", "visibility": "all"}}}
        errors, _ = validate_org_secret_files(_org(data), REPOS)
        assert any("GITHUB_ENV_NAME" in e for e in errors)

    def test_literal_secret_value_is_error_and_not_echoed(self):
        data = {
            "actions_secrets": {
                "TOKEN": {"value": "plain-literal-secret-xyz", "visibility": "all"}
            }
        }
        errors, _ = validate_org_secret_files(_org(data), REPOS)
        assert len(errors) == 1
        assert "env:VAR_NAME" in errors[0]
        assert "plain-literal-secret-xyz" not in errors[0]

    def test_missing_secret_value_is_error(self):
        data = {"dependabot_secrets": {"TOKEN": {"visibility": "all"}}}
        errors, _ = validate_org_secret_files(_org(data), REPOS)
        assert any("'value' must be an env:VAR_NAME" in e for e in errors)

    def test_variable_accepts_number_and_bool_but_not_mapping(self):
        ok = {"actions_variables": {"A": {"value": True, "visibility": "all"}, "B": {"value": 3, "visibility": "all"}}}
        assert validate_org_secret_files(_org(ok), REPOS)[0] == []
        bad = {"actions_variables": {"C": {"value": {"nested": 1}, "visibility": "all"}}}
        assert validate_org_secret_files(_org(bad), REPOS)[0] != []

    @pytest.mark.parametrize("visibility", [None, "public", "internal"])
    def test_invalid_visibility_is_error(self, visibility):
        entry = {"value": "env:X"}
        if visibility is not None:
            entry["visibility"] = visibility
        errors, _ = validate_org_secret_files(_org({"actions_secrets": {"X": entry}}), REPOS)
        assert any("'visibility' must be one of" in e for e in errors)

    def test_selected_requires_list(self):
        data = {"actions_secrets": {"X": {"value": "env:X", "visibility": "selected"}}}
        errors, _ = validate_org_secret_files(_org(data), REPOS)
        assert any("requires 'selected_repositories'" in e for e in errors)

    def test_selected_unknown_repo_is_error(self):
        data = {
            "actions_secrets": {
                "X": {
                    "value": "env:X",
                    "visibility": "selected",
                    "selected_repositories": ["repo-a", "ghost"],
                }
            }
        }
        errors, _ = validate_org_secret_files(_org(data), REPOS)
        assert len(errors) == 1
        assert "'ghost'" in errors[0]

    def test_selected_repositories_without_selected_warns(self):
        data = {
            "actions_secrets": {
                "X": {
                    "value": "env:X",
                    "visibility": "all",
                    "selected_repositories": ["repo-a"],
                }
            }
        }
        errors, warnings = validate_org_secret_files(_org(data), REPOS)
        assert errors == []
        assert len(warnings) == 1
        assert "ignored unless visibility is 'selected'" in warnings[0]

    def test_comment_only_file_is_ignored(self):
        assert validate_org_secret_files({"examples.yml": {}}, REPOS) == ([], [])

    def test_non_mapping_file_is_error(self):
        errors, _ = validate_org_secret_files({"bad.yml": ["a", "b"]}, REPOS)
        assert any("top level must be a mapping" in e for e in errors)

    def test_null_type_map_is_ignored(self):
        assert validate_org_secret_files(_org({"actions_secrets": None}), REPOS) == ([], [])


class TestRepoSecretBlocks:
    def test_valid_group_and_repo_blocks(self):
        groups = {
            "base": {
                "secrets": {"actions": {"TOKEN": {"value": "env:TOKEN"}}},
                "variables": {"actions": {"ENV": {"value": "staging"}}},
            }
        }
        repos = {
            "repo-a": {
                "secrets": {"dependabot": {"PW": {"value": "env:PW"}}},
            }
        }
        assert validate_all_repo_secret_blocks(groups, repos) == []

    def test_unknown_secret_type_is_error(self):
        errors = validate_all_repo_secret_blocks(
            {}, {"repo-a": {"secrets": {"codespaces": {"X": {"value": "env:X"}}}}}
        )
        assert any("unknown key 'secrets.codespaces'" in e for e in errors)

    def test_unknown_variable_type_is_error(self):
        errors = validate_all_repo_secret_blocks(
            {}, {"repo-a": {"variables": {"dependabot": {"X": {"value": "1"}}}}}
        )
        assert any("unknown key 'variables.dependabot'" in e for e in errors)

    def test_visibility_is_not_allowed_at_repo_level(self):
        errors = validate_all_repo_secret_blocks(
            {}, {"repo-a": {"secrets": {"actions": {"X": {"value": "env:X", "visibility": "all"}}}}}
        )
        assert any("unknown key 'visibility'" in e for e in errors)

    def test_group_literal_secret_is_error(self):
        errors = validate_all_repo_secret_blocks(
            {"base": {"secrets": {"actions": {"TOKEN": {"value": "literal-value"}}}}}, {}
        )
        assert len(errors) == 1
        assert "literal-value" not in errors[0]

    def test_invalid_repo_variable_name_is_error(self):
        errors = validate_all_repo_secret_blocks(
            {}, {"repo-a": {"variables": {"actions": {"bad": {"value": "x"}}}}}
        )
        assert any("'bad'" in e for e in errors)


class TestLoadSecretFiles:
    def test_missing_directory_returns_empty(self, tmp_path):
        assert load_secret_files(tmp_path / "absent") == {}

    def test_loads_per_file_and_treats_comment_only_as_empty(self, tmp_path):
        (tmp_path / "a.yml").write_text("actions_secrets:\n  X:\n    value: env:X\n")
        (tmp_path / "b.yml").write_text("# only a comment\n")
        files = load_secret_files(tmp_path)
        assert set(files) == {"a.yml", "b.yml"}
        assert files["b.yml"] == {}
        assert files["a.yml"]["actions_secrets"]["X"]["value"] == "env:X"

    def test_shipped_config_validates_cleanly(self):
        config_dir = Path(__file__).parent.parent / "config" / "secret"
        errors, _ = validate_org_secret_files(load_secret_files(config_dir), REPOS)
        assert errors == []
