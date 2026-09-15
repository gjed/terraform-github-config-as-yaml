"""Tests for --config-dir targeting in validate-config.py.

The script previously hardcoded the repository's own config/ directory, so
pointing it at another config tree silently validated the wrong files. That is
how two bugs in the e2e fixture's configuration survived to a live run.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

validate_config = importlib.import_module("validate-config")
set_config_dir = validate_config.set_config_dir
DEFAULT_CONFIG_DIR = validate_config.DEFAULT_CONFIG_DIR


def _restore_default():
    set_config_dir(DEFAULT_CONFIG_DIR)


class TestSetConfigDir:
    """set_config_dir() rebinds every directory constant."""

    def teardown_method(self):
        _restore_default()

    def test_rebinds_all_directories(self, tmp_path):
        set_config_dir(tmp_path)

        assert validate_config.CONFIG_DIR == tmp_path
        assert validate_config.GROUP_DIR == tmp_path / "group"
        assert validate_config.REPOSITORY_DIR == tmp_path / "repository"
        assert validate_config.RULESET_DIR == tmp_path / "ruleset"
        assert validate_config.TEAM_DIR == tmp_path / "team"
        assert validate_config.MEMBERSHIP_DIR == tmp_path / "membership"
        assert validate_config.WEBHOOK_DIR == tmp_path / "webhook"
        assert validate_config.BRANCH_PROTECTION_DIR == tmp_path / "branch-protection"

    def test_restores_to_default(self, tmp_path):
        set_config_dir(tmp_path)
        set_config_dir(DEFAULT_CONFIG_DIR)

        assert validate_config.CONFIG_DIR == DEFAULT_CONFIG_DIR
        assert validate_config.GROUP_DIR == DEFAULT_CONFIG_DIR / "group"

    def test_default_points_at_repository_config(self):
        assert DEFAULT_CONFIG_DIR.name == "config"
        assert (DEFAULT_CONFIG_DIR / "config.yml").exists()


class TestFixtureConfigIsValidated:
    """The e2e fixture's config must actually be reachable by the validator.

    Guards the regression directly: if targeting silently falls back to the
    repository's own config/, these counts collapse to the template's.
    """

    def teardown_method(self):
        _restore_default()

    def test_fixture_config_dir_exists(self):
        fixture = Path(__file__).parent / "e2e" / "config"
        assert fixture.is_dir()

    def test_fixture_loads_its_own_teams(self):
        fixture = Path(__file__).parent / "e2e" / "config"
        set_config_dir(fixture)

        teams = validate_config.load_team_directory(validate_config.TEAM_DIR)
        # The template ships no teams; the fixture ships a three-tier hierarchy.
        assert teams, "fixture teams were not loaded — targeting fell back to config/"

    def test_fixture_loads_more_repositories_than_template(self):
        fixture = Path(__file__).parent / "e2e" / "config"

        set_config_dir(DEFAULT_CONFIG_DIR)
        template_repos = validate_config.load_repository_config(
            validate_config.REPOSITORY_DIR, []
        )

        set_config_dir(fixture)
        fixture_repos = validate_config.load_repository_config(
            validate_config.REPOSITORY_DIR, []
        )

        assert fixture_repos != template_repos
