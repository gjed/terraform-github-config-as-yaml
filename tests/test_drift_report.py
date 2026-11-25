"""Tests for scripts/drift_report.py over committed plan JSON fixtures."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import drift_report  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "drift"
WEB_REPO = 'module.repositories["web"].github_repository.this'


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


def report_for(name: str) -> dict:
    return drift_report.analyse(load(name))


def changes_by_address(report: dict) -> dict:
    return {c["address"]: c for g in report["groups"] for c in g["changes"]}


class TestClassify:
    @pytest.mark.parametrize(
        "actions,expected",
        [
            (["create"], "create"),
            (["update"], "update"),
            (["delete"], "delete"),
            (["delete", "create"], "replace"),
            (["create", "delete"], "replace"),
            (["no-op"], None),
            (["read"], None),
            ([], None),
            (["forget"], "other"),
        ],
    )
    def test_actions(self, actions, expected):
        assert drift_report.classify(actions) == expected


class TestNoDrift:
    def test_noop_and_read_are_ignored(self):
        report = report_for("no_drift")
        assert report["drift"] is False
        assert report["groups"] == []
        assert report["summary"]["changes"] == 0
        assert drift_report.exit_code(report) == drift_report.EXIT_OK

    def test_plan_without_resource_changes(self):
        assert drift_report.analyse({"format_version": "1.2"})["drift"] is False

    @pytest.mark.parametrize("fmt", ["text", "markdown"])
    def test_message(self, fmt):
        assert "No drift detected." in drift_report.render(report_for("no_drift"), fmt)

    def test_json(self):
        data = json.loads(drift_report.render(report_for("no_drift"), "json"))
        assert data["drift"] is False
        assert data["groups"] == []


class TestCategories:
    def test_create_update_delete_grouped_by_repository(self):
        report = report_for("multi_repo")
        assert [g["name"] for g in report["groups"]] == ["new-svc", "web", drift_report.ORG_GROUP]
        by_group = {g["name"]: sorted(c["action"] for c in g["changes"]) for g in report["groups"]}
        assert by_group["new-svc"] == ["create", "create"]
        assert by_group["web"] == ["delete", "update"]
        assert by_group[drift_report.ORG_GROUP] == ["update"]
        assert "stable" not in by_group

    def test_summary_counts(self):
        summary = report_for("multi_repo")["summary"]
        assert summary["changes"] == 5
        assert summary["groups"] == 3
        assert (summary["create"], summary["update"], summary["delete"], summary["replace"]) == (2, 2, 1, 0)
        assert summary["critical"] == 0

    def test_non_critical_drift_exits_2(self):
        assert drift_report.exit_code(report_for("multi_repo")) == drift_report.EXIT_DRIFT

    def test_update_lists_changed_attributes_only(self):
        web = changes_by_address(report_for("multi_repo"))[WEB_REPO]
        attrs = {a["path"]: (a["before"], a["after"]) for a in web["attributes"]}
        assert attrs == {"has_issues": (True, False), "topics.1": (None, "frontend")}

    def test_resource_is_relative_to_module(self):
        assert changes_by_address(report_for("multi_repo"))[WEB_REPO]["resource"] == "github_repository.this"

    def test_unknown_after_apply(self):
        plan = {
            "format_version": "1.2",
            "resource_changes": [
                {
                    "address": "github_organization_settings.this",
                    "type": "github_organization_settings",
                    "change": {
                        "actions": ["update"],
                        "before": {"etag": "abc"},
                        "after": {},
                        "after_unknown": {"etag": True},
                    },
                }
            ],
        }
        (change,) = drift_report.analyse(plan)["groups"][0]["changes"]
        assert change["attributes"] == [{"path": "etag", "before": "abc", "after": drift_report.UNKNOWN}]


class TestCritical:
    def test_repository_destroy(self):
        report = report_for("repo_destroy")
        repo = changes_by_address(report)['module.repositories["old-repo"].github_repository.this']
        assert repo["action"] == "delete"
        assert repo["critical"] is True
        assert repo["reasons"] == ["repository would be destroyed"]
        assert report["repository_destroyed"] is True
        assert drift_report.exit_code(report) == drift_report.EXIT_CRITICAL

    def test_repository_replace(self):
        report = report_for("repo_replace")
        (change,) = report["groups"][0]["changes"]
        assert change["action"] == "replace"
        assert change["critical"] is True
        assert "replaced" in change["reasons"][0]
        assert drift_report.exit_code(report) == drift_report.EXIT_CRITICAL

    def test_visibility_private_to_public(self):
        report = report_for("update_visibility")
        repo = changes_by_address(report)['module.repositories["app"].github_repository.this']
        assert repo["reasons"] == ["security: visibility private -> public"]
        assert {a["path"] for a in repo["attributes"]} == {"visibility", "description"}
        assert report["summary"]["critical"] == 1

    def test_security_weakening_is_critical_but_not_a_hard_failure(self):
        report = report_for("update_visibility")
        assert report["repository_destroyed"] is False
        assert drift_report.exit_code(report) == drift_report.EXIT_DRIFT

    def test_protection_changes(self):
        report = report_for("protections_weakened")
        reasons = {c["resource"]: c["reasons"] for c in changes_by_address(report).values()}
        assert reasons == {
            'github_branch_protection.this["main-protection"]': ["security: protection deleted"],
            'github_branch_protection.this["release-protection"]': ["security: required signatures removed"],
            'github_repository_ruleset.this["disabled"]': ["security: enforcement disabled"],
            'github_repository_ruleset.this["gone"]': ["security: protection deleted"],
            'github_repository_ruleset.this["unsigned"]': ["security: required signatures removed"],
            'github_organization_ruleset.this["org-main"]': ["security: enforcement disabled"],
        }
        assert report["summary"]["critical"] == 6

    def test_visibility_public_to_private_is_not_critical(self):
        plan = load("update_visibility")
        change = plan["resource_changes"][0]["change"]
        change["before"]["visibility"], change["after"]["visibility"] = "public", "private"
        assert drift_report.analyse(plan)["summary"]["critical"] == 0

    def test_critical_listed_before_groups_in_text(self):
        text = drift_report.render(report_for("update_visibility"), "text")
        assert text.index("CRITICAL") < text.index("Repository: app")


class TestSensitive:
    @pytest.mark.parametrize("fmt", ["text", "markdown", "json"])
    def test_values_never_printed(self, fmt):
        out = drift_report.render(report_for("sensitive"), fmt)
        assert "hunter2" not in out
        assert "db-hunter2" not in out
        assert "(sensitive)" in out

    def test_masked_attribute(self):
        change = changes_by_address(report_for("sensitive"))['github_actions_organization_secret.this["DEPLOY_TOKEN"]']
        attrs = {a["path"]: a for a in change["attributes"]}
        assert attrs["plaintext_value"]["before"] == drift_report.SENSITIVE
        assert attrs["plaintext_value"]["after"] == drift_report.SENSITIVE
        assert attrs["visibility"]["after"] == "private"

    def test_unchanged_sensitive_attribute_is_not_listed(self):
        plan = load("sensitive")
        change = plan["resource_changes"][0]["change"]
        change["after"]["plaintext_value"] = change["before"]["plaintext_value"]
        org_group = drift_report.analyse(plan)["groups"][-1]
        attrs = org_group["changes"][0]["attributes"]
        assert [a["path"] for a in attrs] == ["visibility"]


class TestFormats:
    def test_text_plain_has_no_escape_sequences(self):
        assert "\033[" not in drift_report.render(report_for("protections_weakened"), "text", color=False)

    def test_text_color_adds_escape_sequences(self):
        assert "\033[" in drift_report.render(report_for("protections_weakened"), "text", color=True)

    def test_text_layout(self):
        text = drift_report.render(report_for("multi_repo"), "text")
        assert "Drift detected: 5 change(s) in 3 group(s) (2 create, 2 update, 1 delete)" in text
        assert "Repository: web" in text
        assert "Organization-level resources" in text
        assert "      has_issues: true -> false" in text

    def test_markdown_layout(self):
        md = drift_report.render(report_for("update_visibility"), "markdown")
        assert md.startswith("## Drift report\n")
        assert "### Critical (1)" in md
        assert "### Repository `app`" in md
        assert '`visibility`: `"private"` → `"public"`' in md
        assert "\033[" not in md

    def test_json_structure(self):
        data = json.loads(drift_report.render(report_for("repo_destroy"), "json"))
        assert set(data) == {"drift", "summary", "critical", "groups"}
        assert data["drift"] is True
        assert data["summary"]["critical"] == 2
        assert data["critical"][0]["group"] == "old-repo"
        assert data["groups"][0]["name"] == "old-repo"
        assert data["groups"][0]["changes"][0]["action"] == "delete"


class TestMain:
    @staticmethod
    def run(argv, capsys):
        code = drift_report.main(argv)
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    @pytest.mark.parametrize(
        "name,code",
        [
            ("no_drift", 0),
            ("multi_repo", 2),
            ("update_visibility", 2),
            ("repo_destroy", 3),
            ("repo_replace", 3),
        ],
    )
    def test_exit_codes(self, name, code, capsys):
        assert self.run([str(FIXTURES / f"{name}.json")], capsys)[0] == code

    def test_format_flag(self, capsys):
        code, out, _ = self.run([str(FIXTURES / "multi_repo.json"), "--format", "json"], capsys)
        assert code == 2
        assert json.loads(out)["summary"]["changes"] == 5

    def test_reads_stdin(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "stdin", io.StringIO((FIXTURES / "no_drift.json").read_text()))
        code, out, _ = self.run(["-"], capsys)
        assert code == 0
        assert "No drift detected." in out

    def test_missing_file(self, capsys):
        code, out, err = self.run([str(FIXTURES / "missing.json")], capsys)
        assert (code, out) == (1, "")
        assert "drift_report:" in err

    def test_invalid_json(self, capsys, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json")
        code, out, err = self.run([str(bad)], capsys)
        assert (code, out) == (1, "")
        assert "drift_report:" in err

    def test_not_a_plan(self, capsys, tmp_path):
        other = tmp_path / "other.json"
        other.write_text('{"hello": "world"}')
        code, _, err = self.run([str(other)], capsys)
        assert code == 1
        assert "not Terraform plan JSON" in err

    def test_bad_format_exits_1(self):
        with pytest.raises(SystemExit) as exc:
            drift_report.main(["--format", "yaml"])
        assert exc.value.code == 1
