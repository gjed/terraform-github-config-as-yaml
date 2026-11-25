#!/usr/bin/env python3
"""
Turn Terraform plan JSON into a drift report.

Reads the output of `terraform show -json <planfile>`, ignores no-op and read
entries, groups the remaining resource changes by repository and flags critical
ones: a destroyed or replaced github_repository, and changes that weaken
security (visibility private -> public, a branch protection or ruleset deleted
or disabled, required signatures removed). Values the plan marks sensitive are
printed as "(sensitive)", never as values.

Usage:
    terraform show -json tfplan | python scripts/drift_report.py
    python scripts/drift_report.py plan.json --format markdown
    python scripts/drift_report.py plan.json --format json

Exit codes:
    0  no resource changes
    1  error (unreadable or invalid input, bad arguments)
    2  resource changes (drift)
    3  a github_repository would be destroyed or replaced
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_DRIFT = 2
EXIT_CRITICAL = 3

IGNORED_ACTIONS = {"no-op", "read"}
SENSITIVE = "(sensitive)"
UNKNOWN = "(known after apply)"
ORG_GROUP = "(organization)"
FORMATS = ("text", "markdown", "json")

REPO_MODULE_RE = re.compile(r'module\.repositories\["([^"]+)"\]')
PROTECTION_TYPES = {
    "github_branch_protection",
    "github_repository_ruleset",
    "github_organization_ruleset",
}
KIND_ORDER = ("create", "update", "delete", "replace", "other")
SYMBOLS = {"create": "+", "update": "~", "delete": "-", "replace": "-/+", "other": "?"}
COLORS = {"create": "32", "update": "33", "delete": "31", "replace": "35", "other": "36"}
MAX_VALUE_LENGTH = 120

_MISSING = object()


class PlanError(Exception):
    """The input is not a usable Terraform plan JSON document."""


def classify(actions):
    """Return create/update/delete/replace/other, or None for no-op and read."""
    acts = set(actions) - IGNORED_ACTIONS
    if not acts:
        return None
    if {"create", "delete"} <= acts:
        return "replace"
    for kind in ("delete", "create", "update"):
        if kind in acts:
            return kind
    return "other"


def group_of(resource_change):
    """Repository name for resources inside a repository module, else the org group."""
    module = resource_change.get("module_address") or resource_change.get("address", "")
    match = REPO_MODULE_RE.search(module)
    return match.group(1) if match else ORG_GROUP


def _leaves(value, mask, path, out):
    """Flatten value into path -> (leaf, is_sensitive), honouring a *_sensitive mask."""
    if mask is True or not value or not isinstance(value, (dict, list)):
        out[path] = (value, mask is True)
    elif isinstance(value, dict):
        for key, child in value.items():
            child_mask = mask.get(key) if isinstance(mask, dict) else None
            _leaves(child, child_mask, f"{path}.{key}" if path else key, out)
    else:
        for index, child in enumerate(value):
            child_mask = mask[index] if isinstance(mask, list) and index < len(mask) else None
            _leaves(child, child_mask, f"{path}.{index}" if path else str(index), out)


def _unknown_paths(unknown, path, out):
    if unknown is True:
        out.add(path)
    elif isinstance(unknown, dict):
        for key, child in unknown.items():
            _unknown_paths(child, f"{path}.{key}" if path else key, out)
    elif isinstance(unknown, list):
        for index, child in enumerate(unknown):
            _unknown_paths(child, f"{path}.{index}" if path else str(index), out)


def diff_attributes(change):
    """List changed attributes as {path, before, after}; sensitive values are masked."""
    before, after = {}, {}
    _leaves(change.get("before") or {}, change.get("before_sensitive"), "", before)
    _leaves(change.get("after") or {}, change.get("after_sensitive"), "", after)
    unknown = set()
    _unknown_paths(change.get("after_unknown"), "", unknown)
    for path in unknown:
        after[path] = (UNKNOWN, False)

    attributes = []
    for path in sorted((set(before) | set(after)) - {""}):
        old, old_masked = before.get(path, (_MISSING, False))
        new, new_masked = after.get(path, (_MISSING, False))
        if old == new:
            continue
        masked = old_masked or new_masked
        attributes.append(
            {
                "path": path,
                "before": None if old is _MISSING else (SENSITIVE if masked else old),
                "after": None if new is _MISSING else (SENSITIVE if masked else new),
            }
        )
    return attributes


def _signatures_required(rtype, values):
    if rtype == "github_branch_protection":
        return values.get("require_signed_commits") is True
    rules = values.get("rules")
    return isinstance(rules, list) and any(
        isinstance(rule, dict) and rule.get("required_signatures") is True for rule in rules
    )


def critical_reasons(rtype, kind, before, after):
    """Reasons a change is critical; an empty list means it is not."""
    reasons = []
    if rtype == "github_repository":
        if kind == "delete":
            reasons.append("repository would be destroyed")
        elif kind == "replace":
            reasons.append("repository would be replaced (destroyed and recreated)")
        elif kind == "update":
            old, new = before.get("visibility"), after.get("visibility")
            if old in ("private", "internal") and new == "public":
                reasons.append(f"security: visibility {old} -> public")
    elif rtype in PROTECTION_TYPES:
        if kind == "delete":
            reasons.append("security: protection deleted")
        elif kind == "update":
            if before.get("enforcement") != "disabled" and after.get("enforcement") == "disabled":
                reasons.append("security: enforcement disabled")
            if _signatures_required(rtype, before) and not _signatures_required(rtype, after):
                reasons.append("security: required signatures removed")
    return reasons


def analyse(plan):
    """Categorise a parsed plan into a summary, critical findings and per-group changes."""
    if not isinstance(plan, dict) or "format_version" not in plan:
        raise PlanError("input is not Terraform plan JSON (no format_version); use `terraform show -json`")

    groups = {}
    repository_destroyed = False
    for resource_change in plan.get("resource_changes") or []:
        change = resource_change.get("change") or {}
        kind = classify(change.get("actions") or [])
        if kind is None:
            continue
        rtype = resource_change.get("type", "")
        address = resource_change.get("address", "")
        module = resource_change.get("module_address")
        reasons = critical_reasons(rtype, kind, change.get("before") or {}, change.get("after") or {})
        if rtype == "github_repository" and kind in ("delete", "replace"):
            repository_destroyed = True
        group = group_of(resource_change)
        groups.setdefault(group, []).append(
            {
                "address": address,
                "resource": address[len(module) + 1 :] if module and address.startswith(module + ".") else address,
                "type": rtype,
                "group": group,
                "action": kind,
                "critical": bool(reasons),
                "reasons": reasons,
                "attributes": diff_attributes(change) if kind in ("update", "replace") else [],
            }
        )

    ordered = sorted(groups, key=lambda name: (name == ORG_GROUP, name))
    group_list = [{"name": name, "changes": sorted(groups[name], key=lambda c: c["address"])} for name in ordered]
    changes = [c for g in group_list for c in g["changes"]]
    critical = [c for c in changes if c["critical"]]
    summary = {"changes": len(changes), "groups": len(group_list), "critical": len(critical)}
    for kind in KIND_ORDER:
        summary[kind] = sum(1 for c in changes if c["action"] == kind)
    return {
        "drift": bool(changes),
        "summary": summary,
        "critical": [
            {k: c[k] for k in ("address", "group", "action", "reasons")} for c in critical
        ],
        "groups": group_list,
        "repository_destroyed": repository_destroyed,
    }


def exit_code(report):
    if report["repository_destroyed"]:
        return EXIT_CRITICAL
    return EXIT_DRIFT if report["drift"] else EXIT_OK


def _format_value(value):
    if value in (SENSITIVE, UNKNOWN):
        return value
    text = json.dumps(value)
    return text if len(text) <= MAX_VALUE_LENGTH else text[: MAX_VALUE_LENGTH - 3] + "..."


def _counts(summary):
    parts = [f"{summary[k]} {k}" for k in KIND_ORDER if summary[k]]
    return ", ".join(parts)


def _group_title(name):
    return "Organization-level resources" if name == ORG_GROUP else f"Repository: {name}"


def render_text(report, color=False):
    def paint(code, text):
        return f"\033[{code}m{text}\033[0m" if color else text

    if not report["drift"]:
        return paint("32", "No drift detected.") + "\n"

    summary = report["summary"]
    lines = [
        paint("1", f"Drift detected: {summary['changes']} change(s) in {summary['groups']} group(s)")
        + f" ({_counts(summary)})"
    ]
    if report["critical"]:
        lines += ["", paint("1;31", f"CRITICAL ({summary['critical']})")]
        for finding in report["critical"]:
            lines.append(f"  {paint('31', '!')} {finding['address']}")
            for reason in finding["reasons"]:
                lines.append(f"      {paint('31', reason)}")
    for group in report["groups"]:
        lines += ["", paint("1", _group_title(group["name"]))]
        for change in group["changes"]:
            symbol = paint(COLORS[change["action"]], SYMBOLS[change["action"]])
            flag = " " + paint("1;31", "CRITICAL") if change["critical"] else ""
            lines.append(f"  {symbol} {change['resource']} ({change['action']}){flag}")
            for attr in change["attributes"]:
                lines.append(
                    f"      {attr['path']}: {_format_value(attr['before'])} -> {_format_value(attr['after'])}"
                )
    return "\n".join(lines) + "\n"


def _code(text):
    return "`" + str(text).replace("`", "'") + "`"


def render_markdown(report):
    if not report["drift"]:
        return "## Drift report\n\nNo drift detected.\n"

    summary = report["summary"]
    lines = [
        "## Drift report",
        "",
        f"{summary['changes']} change(s) in {summary['groups']} group(s): {_counts(summary)}.",
    ]
    if report["critical"]:
        lines += ["", f"### Critical ({summary['critical']})", ""]
        for finding in report["critical"]:
            lines.append(f"- {_code(finding['address'])}: {'; '.join(finding['reasons'])}")
    for group in report["groups"]:
        title = "Organization-level resources" if group["name"] == ORG_GROUP else f"Repository {_code(group['name'])}"
        lines += ["", f"### {title}", ""]
        for change in group["changes"]:
            flag = " **(critical)**" if change["critical"] else ""
            lines.append(f"- {_code(change['resource'])}: {change['action']}{flag}")
            for attr in change["attributes"]:
                lines.append(
                    f"  - {_code(attr['path'])}: {_code(_format_value(attr['before']))}"
                    f" → {_code(_format_value(attr['after']))}"
                )
    return "\n".join(lines) + "\n"


def render_json(report):
    public = {k: v for k, v in report.items() if k != "repository_destroyed"}
    return json.dumps(public, indent=2) + "\n"


def render(report, fmt, color=False):
    if fmt == "json":
        return render_json(report)
    if fmt == "markdown":
        return render_markdown(report)
    return render_text(report, color)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        sys.exit(EXIT_ERROR)


def main(argv=None):
    parser = _Parser(description="Summarise a Terraform plan JSON as a drift report.")
    parser.add_argument("plan", nargs="?", default="-", help="plan JSON file, or - for stdin (default)")
    parser.add_argument("--format", choices=FORMATS, default="text", help="output format (default: text)")
    args = parser.parse_args(argv)

    try:
        if args.plan == "-":
            plan = json.load(sys.stdin)
        else:
            with open(args.plan, encoding="utf-8") as handle:
                plan = json.load(handle)
        report = analyse(plan)
    except (OSError, ValueError, PlanError) as err:
        print(f"drift_report: {err}", file=sys.stderr)
        return EXIT_ERROR

    color = sys.stdout.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"
    sys.stdout.write(render(report, args.format, color))
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
