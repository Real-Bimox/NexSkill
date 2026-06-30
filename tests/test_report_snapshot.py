"""Markdown report snapshot coverage.

Golden-file tests pin the exact owner-facing Markdown for representative report
states. The reports are built from fixed inputs with a fixed ``generated_at`` so
the output is byte-stable. Regenerate intentionally with:

    NEXSKILL_UPDATE_SNAPSHOTS=1 python -m pytest tests/test_report_snapshot.py

and review the diff before committing.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from nexskill.contracts import CheckOutcome, CheckResult, PlanResult, PlanStep
from nexskill.report import build_report, render_markdown

SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"
FIXED_TIME = "2026-06-30T00:00:00Z"


def _plan():
    return PlanResult(
        task="add a small repo change",
        stages=["planning", "building"],
        steps=[
            PlanStep("planning.task-breakdown", "Task Breakdown",
                     "Breaks work into verifiable tasks.", "planning",
                     "Matched the task by 2 keyword(s)."),
            PlanStep("building.implementation", "Implementation",
                     "Writes the change in small slices.", "building",
                     "Included as a prerequisite (depends_on)."),
        ],
        conflicts=[],
        warnings=[],
    )


def _passing_report():
    rep = build_report(
        task="add a small repo change",
        plan=_plan(),
        check=CheckResult(
            op="check", status="passed",
            checks=[CheckOutcome("config", "(internal)", True, "passed", "Config present and valid."),
                    CheckOutcome("git-clean", "(internal)", False, "skipped", "Not a git repository; skipped.")],
            blockers=[], warnings=[],
        ),
        project_name="demo", repo_root=Path("."),
        extra_sections={"performance": {"plan_ms": 12, "check_ms": 5}},
    )
    rep["generated_at"] = FIXED_TIME
    return rep


def _failing_report():
    rep = build_report(
        task=None, plan=None,
        check=CheckResult(
            op="check", status="failed",
            checks=[CheckOutcome("tests", "(internal)", True, "failed", "Command failed.")],
            blockers=["tests: Command failed."], warnings=[],
        ),
        project_name="demo", repo_root=Path("."),
    )
    rep["generated_at"] = FIXED_TIME
    return rep


SNAPSHOTS = {
    "report_passed.md": _passing_report,
    "report_failed.md": _failing_report,
}


class ReportSnapshotTests(unittest.TestCase):
    def test_snapshots_match(self):
        update = os.environ.get("NEXSKILL_UPDATE_SNAPSHOTS") == "1"
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        for filename, builder in SNAPSHOTS.items():
            rendered = render_markdown(builder())
            path = SNAPSHOT_DIR / filename
            if update:
                path.write_text(rendered, encoding="utf-8")
                continue
            self.assertTrue(path.exists(), msg=f"missing snapshot {filename}; regenerate with NEXSKILL_UPDATE_SNAPSHOTS=1")
            expected = path.read_text(encoding="utf-8")
            self.assertEqual(rendered, expected, msg=f"snapshot drift in {filename}")


if __name__ == "__main__":
    unittest.main()
