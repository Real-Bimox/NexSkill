"""Lane E - Report Builder tests.

latest.json shape, Markdown rendering, reproducibility, sensitive-field /
source-name exclusion, and additive future sections.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from nexskill import proof, report
from nexskill.contracts import (
    CheckOutcome,
    CheckResult,
    PlanResult,
    PlanStep,
    REPORT_SCHEMA_VERSION,
)
from nexskill.report import build_report, render_markdown, scan_for_forbidden_names


def _plan():
    return PlanResult(
        task="add a small repo change",
        stages=["planning", "building"],
        steps=[
            PlanStep("planning.task-breakdown", "Task Breakdown", "Breaks work into tasks.", "planning", "Matched the task."),
            PlanStep("building.implementation", "Implementation", "Writes the change.", "building", "Dependency."),
        ],
        conflicts=[],
        warnings=[],
    )


def _check(status="passed"):
    return CheckResult(
        op="check",
        status=status,
        checks=[CheckOutcome("config", "(internal)", True, "passed", "ok")],
        blockers=[] if status != "failed" else ["config: bad"],
        warnings=[] if status != "warning" else ["x: warn"],
    )


class _Repo:
    def __init__(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def cleanup(self):
        self.tmp.cleanup()


class ReportShapeTests(unittest.TestCase):
    def test_json_contains_required_sections(self):
        rep = build_report(
            task="t", plan=_plan(), check=_check(), project_name="demo",
            repo_root=Path("."),
        )
        for key in ("task", "plan", "checks", "status", "blockers", "warnings", "next_action"):
            self.assertIn(key, rep, msg=key)
        self.assertEqual(rep["schema_version"], REPORT_SCHEMA_VERSION)
        self.assertEqual(rep["product"], "NexSkill")

    def test_next_action_reflects_status(self):
        rep = build_report(task="t", plan=_plan(), check=_check("failed"), project_name="d", repo_root=Path("."))
        self.assertIn("failing required checks", rep["next_action"])
        rep2 = build_report(task="t", plan=None, check=None, project_name="d", repo_root=Path("."))
        self.assertIn("plan", rep2["next_action"])

    def test_future_sections_added_additively_without_overwriting(self):
        rep = build_report(
            task="t", plan=None, check=None, project_name="d", repo_root=Path("."),
            extra_sections={"performance": {"plan_ms": 12}, "status": "should-not-overwrite"},
        )
        self.assertEqual(rep["performance"], {"plan_ms": 12})
        # reserved key not overwritten
        self.assertNotEqual(rep["status"], "should-not-overwrite")


class MarkdownTests(unittest.TestCase):
    def test_markdown_is_concise_and_owner_readable(self):
        rep = build_report(task="t", plan=_plan(), check=_check(), project_name="demo", repo_root=Path("."))
        md = render_markdown(rep)
        self.assertIn("# NexSkill report", md)
        self.assertIn("Skill path", md)
        self.assertIn("Task Breakdown", md)
        self.assertIn("Next action", md)
        # owner-decides footer present
        self.assertIn("owner or project process decides", md)


class ExclusionTests(unittest.TestCase):
    def test_source_names_absent_from_report(self):
        rep = build_report(task="t", plan=_plan(), check=_check(), project_name="demo", repo_root=Path("."))
        self.assertEqual(scan_for_forbidden_names(rep), [])

    def test_scan_detects_forbidden_names(self):
        rep = {"product": "NexSkill", "note": "uses skilldag internals"}
        self.assertIn("skilldag", scan_for_forbidden_names(rep))


class ReproducibilityTests(unittest.TestCase):
    def setUp(self):
        self.repo = _Repo()

    def tearDown(self):
        self.repo.cleanup()

    def test_reports_reproducible_from_same_inputs(self):
        a = build_report(task="t", plan=_plan(), check=_check(), project_name="d", repo_root=self.repo.root)
        b = build_report(task="t", plan=_plan(), check=_check(), project_name="d", repo_root=self.repo.root)
        # generated_at differs; compare everything else
        a2 = dict(a); a2.pop("generated_at")
        b2 = dict(b); b2.pop("generated_at")
        self.assertEqual(a2, b2)

    def test_write_report_produces_json_and_md(self):
        rep = build_report(task="t", plan=_plan(), check=_check(), project_name="d", repo_root=self.repo.root)
        json_path, md_path = report.write_report(self.repo.root, rep)
        self.assertTrue(json_path.exists())
        self.assertTrue(md_path.exists())
        loaded = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["task"], "t")
        # json keys sorted for reproducibility
        text = json_path.read_text(encoding="utf-8")
        self.assertEqual(text, json.dumps(json.loads(text), indent=2, ensure_ascii=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
