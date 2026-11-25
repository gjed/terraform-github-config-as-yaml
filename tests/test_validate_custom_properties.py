"""Tests for custom property validation in validate-config.py.

Terraform enforces the same rules in preconditions on github_organization_custom_properties
and github_repository_custom_property; these tests keep the offline validator aligned with it.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

validate_config = importlib.import_module("validate-config")
validate_custom_property_definition = validate_config.validate_custom_property_definition
validate_custom_property_files = validate_config.validate_custom_property_files
validate_all_custom_property_value_blocks = (
    validate_config.validate_all_custom_property_value_blocks
)
validate_required_custom_properties = validate_config.validate_required_custom_properties
validate_custom_properties_tier = validate_config.validate_custom_properties_tier
merge_custom_property_definitions = validate_config.merge_custom_property_definitions
custom_properties_supported = validate_config.custom_properties_supported
VALID_GROUP_KEYS = validate_config.VALID_GROUP_KEYS

DEFINITIONS = {
    "environment": {
        "value_type": "single_select",
        "required": True,
        "default_value": "development",
        "allowed_values": ["development", "staging", "production"],
    },
    "tags": {"value_type": "multi_select", "allowed_values": ["frontend", "backend"]},
    "owner": {"value_type": "string"},
    "is_deprecated": {"value_type": "true_false"},
}


def _definition_errors(definition) -> list[str]:
    return validate_custom_property_definition("prop", definition)


def _value_errors(values: dict, definitions: dict | None = None) -> list[str]:
    repos = {"app": {"groups": [], "custom_property_values": values}}
    return validate_all_custom_property_value_blocks(
        {}, repos, DEFINITIONS if definitions is None else definitions
    )


class TestValidDefinitions:
    def test_all_types_have_no_errors(self):
        for name, definition in DEFINITIONS.items():
            assert validate_custom_property_definition(name, definition) == []

    def test_full_definition_has_no_errors(self):
        definition = {
            "description": "Deployment environment",
            "value_type": "single_select",
            "required": True,
            "default_value": "staging",
            "allowed_values": ["development", "staging"],
            "values_editable_by": "org_and_repo_actors",
        }
        assert _definition_errors(definition) == []

    def test_boolean_default_for_true_false(self):
        assert _definition_errors({"value_type": "true_false", "default_value": False}) == []

    def test_custom_property_values_is_a_valid_group_key(self):
        assert "custom_property_values" in VALID_GROUP_KEYS


class TestInvalidDefinitions:
    @pytest.mark.parametrize("definition", [None, "string", ["string"]])
    def test_definition_must_be_a_mapping(self, definition):
        errors = _definition_errors(definition)
        assert len(errors) == 1
        assert "definition must be a mapping" in errors[0]

    def test_missing_or_bad_value_type(self):
        for definition in ({}, {"value_type": "number"}):
            errors = _definition_errors(definition)
            assert len(errors) == 1
            assert "'value_type' must be one of" in errors[0]

    def test_unknown_key(self):
        errors = _definition_errors({"value_type": "string", "allowed": ["a"]})
        assert errors == ["custom property 'prop': unknown key 'allowed'"]

    def test_select_needs_allowed_values(self):
        for allowed in (None, []):
            definition = {"value_type": "multi_select", "allowed_values": allowed}
            errors = _definition_errors(definition)
            assert len(errors) == 1
            assert "non-empty 'allowed_values'" in errors[0]

    def test_allowed_values_only_for_select_types(self):
        errors = _definition_errors({"value_type": "string", "allowed_values": ["a"]})
        assert len(errors) == 1
        assert "only applies to single_select and multi_select" in errors[0]

    def test_allowed_values_must_be_a_list_of_strings(self):
        for allowed in ("a", [{"a": 1}], [""]):
            errors = _definition_errors(
                {"value_type": "single_select", "allowed_values": allowed}
            )
            assert any("list of non-empty strings" in e for e in errors)

    def test_default_must_be_allowed_for_select_types(self):
        errors = _definition_errors(
            {
                "value_type": "single_select",
                "allowed_values": ["a", "b"],
                "default_value": "c",
            }
        )
        assert len(errors) == 1
        assert "'default_value' must be one of 'allowed_values'" in errors[0]

    def test_default_must_be_a_boolean_for_true_false(self):
        errors = _definition_errors({"value_type": "true_false", "default_value": "maybe"})
        assert len(errors) == 1
        assert "must be true or false" in errors[0]

    def test_default_must_be_a_scalar(self):
        errors = _definition_errors({"value_type": "string", "default_value": ["a"]})
        assert len(errors) == 1
        assert "'default_value' must be a string, number, or boolean" in errors[0]

    def test_bad_values_editable_by(self):
        errors = _definition_errors({"value_type": "string", "values_editable_by": "all"})
        assert len(errors) == 1
        assert "'values_editable_by' must be one of" in errors[0]

    def test_required_must_be_boolean(self):
        errors = _definition_errors({"value_type": "string", "required": "yes"})
        assert errors == ["custom property 'prop': 'required' must be true or false"]


class TestDefinitionFiles:
    def test_comment_only_file_is_ignored(self):
        assert validate_custom_property_files({"empty.yml": None}) == ([], [])

    def test_top_level_must_be_a_mapping(self):
        errors, _ = validate_custom_property_files({"bad.yml": ["a"]})
        assert len(errors) == 1
        assert "config/custom-property/bad.yml" in errors[0]

    def test_errors_name_the_file(self):
        errors, _ = validate_custom_property_files(
            {"a.yml": {"prop": {"value_type": "number"}}}
        )
        assert len(errors) == 1
        assert errors[0].startswith("config/custom-property/a.yml: custom property 'prop'")

    def test_duplicate_property_warns_and_last_file_wins(self):
        files = {
            "a.yml": {"p": {"value_type": "string"}},
            "b.yml": {"p": {"value_type": "true_false"}},
        }
        errors, warnings = validate_custom_property_files(files)
        assert errors == []
        assert len(warnings) == 1
        assert "a.yml, b.yml" in warnings[0]
        assert merge_custom_property_definitions(files)["p"]["value_type"] == "true_false"


class TestValueAssignments:
    def test_valid_values_have_no_errors(self):
        values = {
            "environment": "production",
            "tags": ["frontend", "backend"],
            "owner": "platform",
            "is_deprecated": False,
        }
        assert _value_errors(values) == []

    def test_one_element_list_is_accepted_for_single_value_types(self):
        assert _value_errors({"environment": ["production"]}) == []

    @pytest.mark.parametrize("repo_values", [None, {}])
    def test_empty_block_is_valid(self, repo_values):
        assert _value_errors(repo_values) == []

    def test_undefined_property_names_the_owner(self):
        errors = _value_errors({"nonexistent": "x"})
        assert len(errors) == 1
        assert "repository 'app'" in errors[0]
        assert "'nonexistent' is not defined in config/custom-property/" in errors[0]

    def test_undefined_property_in_a_group(self):
        errors = validate_all_custom_property_value_blocks(
            {"oss": {"custom_property_values": {"nope": "x"}}}, {}, DEFINITIONS
        )
        assert len(errors) == 1
        assert "group 'oss'" in errors[0]

    def test_value_not_in_allowed_values(self):
        errors = _value_errors({"environment": "testing"})
        assert len(errors) == 1
        assert "'testing' not in the allowed values" in errors[0]

    def test_multi_select_values_are_each_checked(self):
        errors = _value_errors({"tags": ["frontend", "critical"]})
        assert len(errors) == 1
        assert "'critical' not in the allowed values" in errors[0]

    def test_list_for_single_value_type(self):
        errors = _value_errors({"environment": ["development", "staging"]})
        assert len(errors) == 1
        assert "takes exactly one value" in errors[0]

    def test_list_for_string_property(self):
        errors = _value_errors({"owner": ["a", "b"]})
        assert len(errors) == 1
        assert "takes exactly one value" in errors[0]

    def test_true_false_takes_a_boolean(self):
        errors = _value_errors({"is_deprecated": "maybe"})
        assert len(errors) == 1
        assert "takes true or false" in errors[0]

    def test_null_empty_and_non_scalar_values(self):
        assert "needs a value" in _value_errors({"owner": None})[0]
        assert "at least one value" in _value_errors({"tags": []})[0]
        assert "string, number, boolean, or a list" in _value_errors({"owner": {"a": 1}})[0]

    def test_block_must_be_a_mapping(self):
        errors = validate_all_custom_property_value_blocks(
            {}, {"app": {"custom_property_values": ["environment"]}}, DEFINITIONS
        )
        assert len(errors) == 1
        assert "must be a mapping" in errors[0]

    def test_no_definitions_means_every_name_is_undefined(self):
        assert len(_value_errors({"environment": "production"}, definitions={})) == 1


class TestRequiredProperties:
    REQUIRED = {"owner": {"value_type": "string", "required": True}}

    def _errors(self, repos, groups=None, definitions=None):
        return validate_required_custom_properties(
            repos, groups or {}, self.REQUIRED if definitions is None else definitions
        )

    def test_missing_on_a_repository(self):
        repos = {
            "orphan-repo": {"groups": []},
            "ok": {"groups": [], "custom_property_values": {"owner": "a"}},
        }
        errors = self._errors(repos)
        assert len(errors) == 1
        assert "'owner' is required" in errors[0]
        assert "do not set it: orphan-repo." in errors[0]

    def test_satisfied_via_group(self):
        groups = {"oss": {"custom_property_values": {"owner": "platform"}}}
        assert self._errors({"app": {"groups": ["oss"]}}, groups) == []

    def test_satisfied_by_default(self):
        definitions = {"owner": {"value_type": "string", "required": True, "default_value": "none"}}
        assert self._errors({"app": {"groups": []}}, definitions=definitions) == []

    def test_optional_property_is_never_required(self):
        definitions = {"owner": {"value_type": "string"}}
        assert self._errors({"app": {"groups": []}}, definitions=definitions) == []

    def test_unknown_group_is_ignored(self):
        assert len(self._errors({"app": {"groups": ["missing"]}})) == 1


class TestTier:
    @pytest.mark.parametrize(
        "config,expected",
        [
            ({"subscription": "team"}, True),
            ({"subscription": "enterprise", "is_organization": True}, True),
            ({"subscription": "free"}, False),
            ({"subscription": "pro"}, False),
            ({"subscription": "team", "is_organization": False}, False),
            ({}, False),
        ],
    )
    def test_supported(self, config, expected):
        assert custom_properties_supported(config) is expected

    def test_supported_tier_has_no_warnings(self):
        repos = {"app": {"groups": [], "custom_property_values": {"owner": "a"}}}
        assert validate_custom_properties_tier({"subscription": "team"}, repos, {}, DEFINITIONS) == []

    def test_free_tier_warns_for_definitions_and_assignments(self):
        repos = {
            "app": {"groups": ["oss"]},
            "plain": {"groups": []},
        }
        groups = {"oss": {"custom_property_values": {"owner": "a"}}}
        warnings = validate_custom_properties_tier({"subscription": "free"}, repos, groups, DEFINITIONS)
        assert len(warnings) == 2
        assert "4 definition(s)" in warnings[0] and "skipped_custom_properties" in warnings[0]
        assert "Repository 'app'" in warnings[1]

    def test_personal_account_warns(self):
        config = {"subscription": "team", "is_organization": False}
        warnings = validate_custom_properties_tier(config, {}, {}, DEFINITIONS)
        assert len(warnings) == 1
        assert "is_organization false" in warnings[0]

    def test_no_configuration_means_no_warnings(self):
        assert validate_custom_properties_tier({"subscription": "free"}, {"a": {"groups": []}}, {}, {}) == []
