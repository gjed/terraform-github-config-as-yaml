"""Tests for subdirectory-aware repository loading in validate-config.py."""

from __future__ import annotations

import sys
from pathlib import Path

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import importlib

validate_config = importlib.import_module("validate-config")
load_repository_config = validate_config.load_repository_config


class TestLoadRepositoryConfig:
    """Test load_repository_config() one-level subdirectory loading."""

    def test_missing_directory_returns_empty(self, tmp_path):
        """Nonexistent repository directory yields no repositories."""
        assert load_repository_config(tmp_path / "nope") == {}

    def test_top_level_files_loaded(self, tmp_path):
        """Top-level *.yml files are loaded."""
        (tmp_path / "repos.yml").write_text("repo1:\n  description: top\n")

        repos = load_repository_config(tmp_path)
        assert set(repos) == {"repo1"}

    def test_all_subdirectories_loaded(self, tmp_path):
        """Every immediate subdirectory contributes its repos."""
        (tmp_path / "oss").mkdir()
        (tmp_path / "oss" / "projects.yml").write_text("oss-repo:\n  description: a\n")
        (tmp_path / "internal").mkdir()
        (tmp_path / "internal" / "utils.yml").write_text("int-repo:\n  description: b\n")

        repos = load_repository_config(tmp_path)
        assert set(repos) == {"oss-repo", "int-repo"}

    def test_top_level_and_subdirectories_merged(self, tmp_path):
        """Top-level and subdirectory files are merged together."""
        (tmp_path / "repos.yml").write_text("top-repo:\n  description: top\n")
        (tmp_path / "oss").mkdir()
        (tmp_path / "oss" / "projects.yml").write_text("oss-repo:\n  description: a\n")

        repos = load_repository_config(tmp_path)
        assert set(repos) == {"top-repo", "oss-repo"}

    def test_subdirectory_key_overrides_top_level(self, tmp_path):
        """Collisions are last-write-wins here; Terraform reports them as duplicates."""
        (tmp_path / "repos.yml").write_text("dup:\n  description: top\n")
        (tmp_path / "oss").mkdir()
        (tmp_path / "oss" / "projects.yml").write_text("dup:\n  description: sub\n")

        repos = load_repository_config(tmp_path)
        assert repos["dup"]["description"] == "sub"

    def test_nested_subdirectories_ignored(self, tmp_path):
        """Only immediate subdirectories are loaded, mirroring Terraform."""
        (tmp_path / "oss").mkdir()
        (tmp_path / "oss" / "projects.yml").write_text("oss-repo:\n  description: a\n")
        (tmp_path / "oss" / "deeper").mkdir()
        (tmp_path / "oss" / "deeper" / "more.yml").write_text("deep:\n  description: x\n")

        repos = load_repository_config(tmp_path)
        assert set(repos) == {"oss-repo"}

    def test_empty_subdirectory_contributes_nothing(self, tmp_path):
        """A subdirectory without YAML files contributes zero repositories."""
        (tmp_path / "repos.yml").write_text("repo1:\n  description: top\n")
        (tmp_path / "empty-dir").mkdir()

        repos = load_repository_config(tmp_path)
        assert set(repos) == {"repo1"}
