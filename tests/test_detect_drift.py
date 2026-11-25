"""Tests for scripts/detect-drift.sh using a stub terraform on PATH.

The stub records its arguments, writes the plan file named by -out, and serves
a fixture as `terraform show -json` output, so exit-code handling and option
mapping are checked without credentials or a real plan.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "detect-drift.sh"
FIXTURES = Path(__file__).parent / "fixtures" / "drift"

STUB = """#!/usr/bin/env bash
case "$1" in
  plan)
    echo "$@" >> "$STUB_LOG"
    for arg in "$@"; do
      case "$arg" in -out=*) echo plan > "${arg#-out=}" ;; esac
    done
    echo "stub plan output"
    exit "${STUB_PLAN_RC:-0}"
    ;;
  show)
    [ "${STUB_SHOW_FAIL:-0}" = 1 ] && exit 1
    cat "$STUB_PLAN_JSON"
    ;;
esac
"""


@pytest.fixture
def run(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "terraform"
    stub.write_text(STUB)
    stub.chmod(0o755)
    log = tmp_path / "terraform.log"

    def _run(fixture="no_drift", plan_rc=0, args=(), show_fail=False):
        env = {
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "STUB_LOG": str(log),
            "STUB_PLAN_JSON": str(FIXTURES / f"{fixture}.json"),
            "STUB_PLAN_RC": str(plan_rc),
            "STUB_SHOW_FAIL": "1" if show_fail else "0",
        }
        proc = subprocess.run(
            ["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env, cwd=tmp_path, check=False
        )
        proc.plan_args = log.read_text().split() if log.exists() else []
        return proc

    return _run


@pytest.mark.parametrize(
    "fixture,plan_rc,expected",
    [
        ("no_drift", 0, 0),
        ("update_visibility", 2, 2),
        ("multi_repo", 2, 2),
        ("repo_destroy", 2, 3),
        ("repo_replace", 2, 3),
        ("no_drift", 2, 0),
    ],
)
def test_exit_code_comes_from_plan_json(run, fixture, plan_rc, expected):
    assert run(fixture, plan_rc).returncode == expected


def test_plan_error_exits_1_without_report(run):
    proc = run("multi_repo", plan_rc=1)
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert "terraform plan failed" in proc.stderr


def test_show_error_exits_1(run):
    proc = run("multi_repo", plan_rc=2, show_fail=True)
    assert proc.returncode == 1
    assert "terraform show failed" in proc.stderr


def test_plan_is_a_full_refresh_with_detailed_exit_code(run):
    proc = run()
    assert "-detailed-exitcode" in proc.plan_args
    assert "-refresh=false" not in proc.plan_args
    assert not any(a.startswith("-target") for a in proc.plan_args)


def test_repo_maps_to_target(run):
    proc = run(args=["--repo", "my-repo"])
    assert '-target=module.repositories["my-repo"]' in proc.plan_args


def test_invalid_repo_name_rejected(run):
    proc = run(args=["--repo", 'x"]; rm'])
    assert proc.returncode == 1
    assert proc.plan_args == []


def test_report_only_on_stdout(run):
    proc = run("multi_repo", 2, ["--format", "json"])
    assert proc.returncode == 2
    assert json.loads(proc.stdout)["summary"]["changes"] == 5
    assert "stub plan output" in proc.stderr


def test_markdown_format(run):
    proc = run("update_visibility", 2, ["--format", "markdown"])
    assert proc.stdout.startswith("## Drift report")


def test_plan_file_is_kept(run, tmp_path):
    plan_file = tmp_path / "kept.tfplan"
    run(args=["--plan-file", str(plan_file)])
    assert plan_file.exists()


def test_temporary_plan_file_is_removed(run):
    proc = run()
    plan_file = next(a for a in proc.plan_args if a.startswith("-out=")).removeprefix("-out=")
    assert not Path(plan_file).exists()


@pytest.mark.parametrize("args", [["--format", "yaml"], ["--bogus"], ["--format"], ["--repo"]])
def test_bad_options_exit_1(run, args):
    proc = run(args=args)
    assert proc.returncode == 1
    assert proc.plan_args == []


def test_help(run):
    proc = run(args=["--help"])
    assert proc.returncode == 0
    assert "--plan-file" in proc.stdout
