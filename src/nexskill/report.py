"""NexSkill report builder.

Produces concise human (Markdown) and machine (JSON) reports from plan/check/
closeout evidence. Reports are reproducible from config and evidence, exclude
raw transcripts, secrets, provider names, and source names, and accept future
sections additively without breaking old reports.

Outputs:

- ``.nexskill/reports/latest.json`` - structured report
- ``.nexskill/reports/latest.md``   - owner-readable summary
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import proof
from .contracts import (
    CheckResult,
    PlanResult,
    PRODUCT_NAME,
    REPORT_SCHEMA_VERSION,
)

#: Names that must never appear in generated NexSkill reports. Sourced project
#: and vendor identities belong only in internal decision records, never in
#: user-facing output. This is the guardrail behind the
#: ``forbid_source_names_in_reports`` policy.
FORBIDDEN_SOURCE_NAMES = (
    "skilldag",
    "autodev",
    "agent-skills",
    "graph-of-skills",
    "real-bimox",
    "openai",
    "gpt",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Report model
# ---------------------------------------------------------------------------


def build_report(
    *,
    task: str | None,
    plan: PlanResult | None,
    check: CheckResult | None,
    project_name: str,
    repo_root: Path,
    extra_sections: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structured report dict.

    The shape is additive: unknown ``extra_sections`` keys are merged in so
    future sections do not break older consumers.
    """
    plan_dict = plan.to_dict() if plan else None
    check_dict = check.to_dict() if check else None

    status = _derive_status(check)
    blockers = check_dict["blockers"] if check_dict else []
    warnings = []
    if plan is not None:
        warnings.extend(plan.warnings)
    if check is not None:
        warnings.extend(check.warnings)

    next_action = _next_action(status, plan is not None, check is not None)

    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generated_at": _utc_now_iso(),
        "product": PRODUCT_NAME,
        "project": project_name,
        "task": task,
        "status": status,
        "plan": plan_dict,
        "checks": check_dict,
        "blockers": blockers,
        "warnings": warnings,
        "next_action": next_action,
    }
    if extra_sections:
        for key, value in extra_sections.items():
            # Never overwrite reserved keys.
            if key not in report:
                report[key] = value
    return report


def _derive_status(check: CheckResult | None) -> str:
    if check is None:
        return "planned"
    return check.status  # passed | failed | warning


def _next_action(status: str, has_plan: bool, has_check: bool) -> str:
    if status == "failed":
        return "Resolve the failing required checks, then re-run `nexskill check`."
    if status == "warning":
        return "Review warnings; if acceptable, run `nexskill closeout` to record evidence."
    if has_check and status == "passed":
        return "Run `nexskill closeout --repo .` to record final evidence."
    if has_plan:
        return "Follow the planned skill path, then run `nexskill check --repo .`."
    return "Run `nexskill plan \"<task>\"` to select a skill path."


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def write_report(repo_root: Path, report: dict[str, Any]) -> tuple[Path, Path]:
    """Write ``latest.json`` and ``latest.md`` atomically into the reports dir."""
    out_dir = proof.reports_dir(repo_root)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "latest.json"
    md_path = out_dir / "latest.md"

    # Deterministic JSON (sorted keys) for reproducibility.
    json_tmp = json_path.with_name(f".{json_path.name}.tmp")
    json_tmp.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    json_tmp.replace(json_path)

    md_tmp = md_path.with_name(f".{md_path.name}.tmp")
    md_tmp.write_text(render_markdown(report), encoding="utf-8")
    md_tmp.replace(md_path)
    return json_path, md_path


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_markdown(report: dict[str, Any]) -> str:
    """Render a concise, owner-readable Markdown report."""
    lines: list[str] = []
    lines.append(f"# {report.get('product', PRODUCT_NAME)} report")
    lines.append("")
    status = report.get("status", "unknown")
    lines.append(f"**Project:** {report.get('project', '')}  ")
    lines.append(f"**Status:** {status}  ")
    task = report.get("task")
    if task:
        lines.append(f"**Task:** {task}  ")
    lines.append(f"**Generated:** {report.get('generated_at', '')}")
    lines.append("")

    plan = report.get("plan")
    if plan:
        lines.append("## Skill path")
        lines.append("")
        stages = plan.get("stages") or []
        if stages:
            lines.append("Stages: " + " → ".join(stages))
            lines.append("")
        steps = plan.get("steps") or []
        if steps:
            for i, step in enumerate(steps, start=1):
                lines.append(f"{i}. **{step.get('name', step.get('skill_id', ''))}** ({step.get('stage', '')})")
                summary = step.get("summary", "")
                if summary:
                    lines.append(f"   {summary}")
                reason = step.get("reason", "")
                if reason:
                    lines.append(f"   _{reason}_")
            lines.append("")
        else:
            lines.append("_No skills selected._")
            lines.append("")

    checks = report.get("checks")
    if checks:
        lines.append("## Checks")
        lines.append("")
        for chk in checks.get("checks", []):
            mark = {"passed": "✓", "failed": "✗", "warning": "!", "skipped": "-"}.get(
                chk.get("status", ""), "?"
            )
            req = "required" if chk.get("required") else "optional"
            lines.append(f"- {mark} **{chk.get('id', '')}** ({req}): {chk.get('message', '')}")
        lines.append("")

    blockers = report.get("blockers") or []
    if blockers:
        lines.append("## Blockers")
        lines.append("")
        for b in blockers:
            lines.append(f"- {b}")
        lines.append("")

    warnings = report.get("warnings") or []
    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("## Next action")
    lines.append("")
    lines.append(report.get("next_action", ""))
    lines.append("")
    lines.append("---")
    lines.append("_NexSkill advises and reports; the owner or project process decides the next action._")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Source-name / secret hygiene guard
# ---------------------------------------------------------------------------


def scan_for_forbidden_names(report: dict[str, Any]) -> list[str]:
    """Return the list of forbidden source names found anywhere in the report
    text. Used by the report builder's self-check and the integration naming
    scan. Empty list means clean."""
    blob = json.dumps(report, ensure_ascii=False).lower()
    found = []
    for name in FORBIDDEN_SOURCE_NAMES:
        if name.lower() in blob:
            found.append(name)
    return found
