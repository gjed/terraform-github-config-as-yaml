"""Tests for the consumer CI/CD templates in ci/ and examples/consumer/.github/workflows/.

The templates are never run by this repository, so nothing else would notice a template that no longer
parses, an action pinned to a mutable tag, or a drift workflow that goes through `make`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parent.parent
CI_DIR = ROOT / "ci"
CONSUMER_WORKFLOWS = ROOT / "examples" / "consumer" / ".github" / "workflows"

YAML_FILES = sorted(
    [
        *CI_DIR.rglob("*.yml"),
        *CI_DIR.rglob("*.yaml"),
        *CONSUMER_WORKFLOWS.glob("*.y*ml"),
    ]
)
WORKFLOWS = [p for p in YAML_FILES if p.parent == CONSUMER_WORKFLOWS or p.parent == CI_DIR / "github-actions"]
DRIFT_WORKFLOWS = [p for p in WORKFLOWS if "drift" in p.name]

USES_RE = re.compile(r"^\s*(?:-\s+)?uses:\s*(?P<ref>\S+)(?P<rest>.*)$")
PINNED_RE = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
VERSION_COMMENT_RE = re.compile(r"^\s*#\s*v\d+(\.\d+){0,2}\s*$")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def test_templates_exist() -> None:
    expected = [
        "ci/README.md",
        "ci/github-actions/terraform-pr.yml",
        "ci/github-actions/terraform-apply.yml",
        "ci/github-actions/terraform-drift.yml",
        "ci/jenkins/Jenkinsfile",
        "ci/docs/authentication.md",
        "ci/backends/s3/backend.tf",
        "ci/backends/gcs/backend.tf",
        "ci/backends/azure/backend.tf",
        "ci/backends/terraform-cloud/backend.tf",
    ]
    assert [p for p in expected if not (ROOT / p).is_file()] == []


@pytest.mark.parametrize("path", YAML_FILES, ids=rel)
def test_yaml_parses(path: Path) -> None:
    assert isinstance(yaml.safe_load(path.read_text()), dict)


@pytest.mark.parametrize("path", WORKFLOWS, ids=rel)
def test_uses_pinned_to_full_sha(path: Path) -> None:
    unpinned = []
    seen = 0
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        match = USES_RE.match(line)
        if not match:
            continue
        seen += 1
        comment = match.group("rest").strip()
        if not PINNED_RE.match(match.group("ref")):
            unpinned.append(f"{number}: {match.group('ref')} is not pinned to a 40-character SHA")
        elif not VERSION_COMMENT_RE.match(" " + comment):
            unpinned.append(f"{number}: {match.group('ref')} lacks a '# vX.Y.Z' comment")
    assert seen > 0, "workflow uses no actions; the check would be vacuous"
    assert unpinned == []


@pytest.mark.parametrize("path", WORKFLOWS, ids=rel)
def test_no_pull_request_target(path: Path) -> None:
    workflow = yaml.safe_load(path.read_text())
    triggers = workflow.get("on", workflow.get(True))
    names = triggers if isinstance(triggers, (list, dict)) else [triggers]
    assert "pull_request_target" not in names


@pytest.mark.parametrize("path", WORKFLOWS, ids=rel)
def test_permissions_declared(path: Path) -> None:
    workflow = yaml.safe_load(path.read_text())
    assert "permissions" in workflow, "declare top-level permissions (use {} and grant per job)"
    for name, job in workflow["jobs"].items():
        assert "permissions" in job, f"job {name} should declare its own minimal permissions"


@pytest.mark.parametrize("path", DRIFT_WORKFLOWS, ids=rel)
def test_drift_workflow_calls_script_not_make(path: Path) -> None:
    runs = []
    for job in yaml.safe_load(path.read_text())["jobs"].values():
        runs.extend(step["run"] for step in job["steps"] if "run" in step)
    commands = "\n".join(runs)
    assert "scripts/detect-drift.sh" in commands
    assert not re.search(r"\bmake\b", commands), "make flattens the drift exit codes to 2"


def test_there_is_a_drift_workflow() -> None:
    assert DRIFT_WORKFLOWS


def test_apply_workflow_is_gated_and_serialised() -> None:
    workflow = yaml.safe_load((CI_DIR / "github-actions" / "terraform-apply.yml").read_text())
    assert workflow["concurrency"]["cancel-in-progress"] is False
    assert all("environment" in job for job in workflow["jobs"].values())


def test_plan_workflow_is_read_only() -> None:
    workflow = yaml.safe_load((CI_DIR / "github-actions" / "terraform-pr.yml").read_text())
    for job in workflow["jobs"].values():
        assert job["permissions"].get("contents") == "read"
        assert "write-all" not in str(job["permissions"])
