"""Tests for partition validation in validate-config.py."""

from __future__ import annotations

import sys
from pathlib import Path

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import importlib

validate_config = importlib.import_module("validate-config")
validate_partitions = validate_config.validate_partitions
load_repository_config = validate_config.load_repository_config


class TestValidatePartitions:
    """Test validate_partitions()."""

    def test_no_partitions_requested_no_errors(self, tmp_path):
        """When no partitions are requested, nothing to validate."""
        errors, warnings = validate_partitions(
            repository_dir=tmp_path,
            requested_partitions=[],
        )
        assert errors == []
        assert warnings == []

    def test_valid_partition_no_errors(self, tmp_path):
        """Requested partition that exists as a subdirectory — no errors."""
        partition_dir = tmp_path / "infra"
        partition_dir.mkdir()
        (partition_dir / "repos.yml").write_text("repo1:\n  description: test\n")

        errors, warnings = validate_partitions(
            repository_dir=tmp_path,
            requested_partitions=["infra"],
        )
        assert errors == []

    def test_invalid_partition_is_error(self, tmp_path):
        """Requested partition that doesn't exist as a subdirectory — error."""
        errors, warnings = validate_partitions(
            repository_dir=tmp_path,
            requested_partitions=["nonexistent"],
        )
        assert len(errors) == 1
        assert "nonexistent" in errors[0]

    def test_multiple_partitions_some_invalid(self, tmp_path):
        """Mix of valid and invalid partitions — only invalid ones flagged."""
        (tmp_path / "infra").mkdir()
        (tmp_path / "apps").mkdir()

        errors, warnings = validate_partitions(
            repository_dir=tmp_path,
            requested_partitions=["infra", "bogus", "apps"],
        )
        assert len(errors) == 1
        assert "bogus" in errors[0]
        assert "infra" not in errors[0] or "Available" in errors[0]

    def test_available_partitions_listed_in_error(self, tmp_path):
        """Error message should list available partitions."""
        (tmp_path / "infra").mkdir()
        (tmp_path / "apps").mkdir()

        errors, warnings = validate_partitions(
            repository_dir=tmp_path,
            requested_partitions=["bogus"],
        )
        assert len(errors) == 1
        assert "infra" in errors[0]
        assert "apps" in errors[0]

    def test_no_available_partitions_message(self, tmp_path):
        """When no subdirectories exist, error says so."""
        errors, warnings = validate_partitions(
            repository_dir=tmp_path,
            requested_partitions=["bogus"],
        )
        assert len(errors) == 1
        assert "bogus" in errors[0]

    def test_files_not_counted_as_partitions(self, tmp_path):
        """Only subdirectories count as partitions, not files."""
        (tmp_path / "not-a-dir.yml").write_text("foo: bar\n")

        errors, warnings = validate_partitions(
            repository_dir=tmp_path,
            requested_partitions=["not-a-dir.yml"],
        )
        assert len(errors) == 1

    def test_empty_partition_dir_warns(self, tmp_path):
        """Partition directory exists but has no YAML files — warning."""
        (tmp_path / "empty-partition").mkdir()

        errors, warnings = validate_partitions(
            repository_dir=tmp_path,
            requested_partitions=["empty-partition"],
        )
        assert errors == []
        assert len(warnings) == 1
        assert "empty-partition" in warnings[0]
        assert "no YAML" in warnings[0] or "no .yml" in warnings[0]


class TestLoadRepositoryConfig:
    """Test load_repository_config() partition-aware loading."""

    def test_missing_directory_returns_empty(self, tmp_path):
        """Nonexistent repository directory yields no repositories."""
        assert load_repository_config(tmp_path / "nope", []) == {}

    def test_top_level_files_loaded(self, tmp_path):
        """Top-level *.yml files are loaded as before."""
        (tmp_path / "repos.yml").write_text("repo1:\n  description: top\n")

        repos = load_repository_config(tmp_path, [])
        assert set(repos) == {"repo1"}

    def test_partition_files_loaded_when_no_partitions_requested(self, tmp_path):
        """Empty --partitions means every discovered partition is active."""
        (tmp_path / "oss").mkdir()
        (tmp_path / "oss" / "projects.yml").write_text("oss-repo:\n  description: a\n")
        (tmp_path / "internal").mkdir()
        (tmp_path / "internal" / "utils.yml").write_text("int-repo:\n  description: b\n")

        repos = load_repository_config(tmp_path, [])
        assert set(repos) == {"oss-repo", "int-repo"}

    def test_only_requested_partitions_loaded(self, tmp_path):
        """Requested partitions filter which subdirectories contribute repos."""
        (tmp_path / "oss").mkdir()
        (tmp_path / "oss" / "projects.yml").write_text("oss-repo:\n  description: a\n")
        (tmp_path / "internal").mkdir()
        (tmp_path / "internal" / "utils.yml").write_text("int-repo:\n  description: b\n")

        repos = load_repository_config(tmp_path, ["oss"])
        assert set(repos) == {"oss-repo"}

    def test_top_level_and_partitions_merged(self, tmp_path):
        """Top-level and partition files are merged together."""
        (tmp_path / "repos.yml").write_text("top-repo:\n  description: top\n")
        (tmp_path / "oss").mkdir()
        (tmp_path / "oss" / "projects.yml").write_text("oss-repo:\n  description: a\n")

        repos = load_repository_config(tmp_path, [])
        assert set(repos) == {"top-repo", "oss-repo"}

    def test_nested_subdirectories_ignored(self, tmp_path):
        """Only immediate partition subdirectories are loaded, mirroring Terraform."""
        (tmp_path / "oss").mkdir()
        (tmp_path / "oss" / "projects.yml").write_text("oss-repo:\n  description: a\n")
        (tmp_path / "oss" / "deeper").mkdir()
        (tmp_path / "oss" / "deeper" / "more.yml").write_text("deep:\n  description: x\n")

        repos = load_repository_config(tmp_path, [])
        assert set(repos) == {"oss-repo"}

    def test_unknown_requested_partition_ignored(self, tmp_path):
        """Invalid partition names are reported by validate_partitions, not here."""
        (tmp_path / "oss").mkdir()
        (tmp_path / "oss" / "projects.yml").write_text("oss-repo:\n  description: a\n")

        repos = load_repository_config(tmp_path, ["bogus"])
        assert repos == {}
