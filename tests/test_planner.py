"""Graph planner tests.

Bounded, deterministic skill paths: seeding, dependency expansion, stage
ordering, conflict surfacing, and reproducibility for identical inputs.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from nexskill.contracts import NexSkillError, SKILL_SCHEMA_VERSION, SkillSource
from nexskill.planner import GraphPlanner
from nexskill.registry import SkillRegistry


def _manifest(package_id, **overrides):
    base = {
        "schema_version": SKILL_SCHEMA_VERSION,
        "id": package_id,
        "name": package_id.replace(".", " ").replace("-", " ").title(),
        "summary": f"Skill {package_id}.",
        "stages": ["planning"],
        "inputs": [],
        "outputs": [],
        "depends_on": [],
        "conflicts_with": [],
        "tags": [],
        "entrypoint": "SKILL.md",
    }
    base.update(overrides)
    return base


class _Repo:
    def __init__(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def add(self, package_id, **overrides):
        d = self.root / "skills" / package_id
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text("# body\n", encoding="utf-8")
        (d / "manifest.json").write_text(json.dumps(_manifest(package_id, **overrides)), encoding="utf-8")

    def registry(self):
        sources = [SkillSource(type="local", path="skills")]
        reg, _ = SkillRegistry.load(sources, self.root)
        return reg

    def cleanup(self):
        self.tmp.cleanup()


class PlannerCoreTests(unittest.TestCase):
    def setUp(self):
        self.repo = _Repo()
        self.repo.add(
            "planning.task-breakdown",
            name="Task Breakdown",
            summary="Breaks a development request into verifiable tasks.",
            stages=["planning"], tags=["planning", "development"],
            outputs=["implementation_plan"],
        )
        self.repo.add(
            "building.implementation",
            name="Implementation",
            summary="Writes code in small slices for a development change.",
            stages=["building"], tags=["building"],
            outputs=["code_change"], depends_on=["planning.task-breakdown"],
        )
        self.repo.add(
            "verifying.testing",
            name="Verification and Testing",
            summary="Adds tests that prove behavior for a change.",
            stages=["verifying"], tags=["testing"],
            outputs=["test_evidence"], depends_on=["building.implementation"],
        )
        self.registry = self.repo.registry()

    def tearDown(self):
        self.repo.cleanup()

    def test_plan_returns_bounded_ordered_path(self):
        planner = GraphPlanner(self.registry)
        result = planner.plan("plan and build a development change")
        ids = [s.skill_id for s in result.steps]
        # dependency expansion pulls planning.task-breakdown in via building
        self.assertIn("building.implementation", ids)
        self.assertIn("planning.task-breakdown", ids)
        # planning stage precedes building stage
        self.assertLess(ids.index("planning.task-breakdown"), ids.index("building.implementation"))
        self.assertLessEqual(len(result.steps), 12)

    def test_plan_is_deterministic(self):
        planner = GraphPlanner(self.registry)
        a = planner.plan("build a development change")
        b = planner.plan("build a development change")
        self.assertEqual(a.to_dict(), b.to_dict())

    def test_empty_task_raises(self):
        planner = GraphPlanner(self.registry)
        with self.assertRaises(NexSkillError) as ctx:
            planner.plan("   ")
        self.assertEqual(ctx.exception.code, "PLAN_NO_TASK")

    def test_dependency_expansion_includes_prerequisite(self):
        planner = GraphPlanner(self.registry)
        result = planner.plan("verify behavior with tests")
        ids = [s.skill_id for s in result.steps]
        # verifying.testing depends_on building.implementation depends_on planning
        if "verifying.testing" in ids:
            self.assertIn("building.implementation", ids)
            self.assertIn("planning.task-breakdown", ids)

    def test_no_match_returns_default_with_warning(self):
        planner = GraphPlanner(self.registry)
        result = planner.plan("zzz qqq nonexistent gibberish words")
        # falls back to planning-stage default rather than empty
        self.assertTrue(len(result.steps) >= 1)
        self.assertTrue(any("default" in w.lower() or "no strong keyword" in w.lower() for w in result.warnings))

    def test_plan_does_not_load_skill_bodies(self):
        planner = GraphPlanner(self.registry)
        result = planner.plan("development change")
        blob = json.dumps(result.to_dict())
        self.assertNotIn("# body", blob)


class PlannerConflictTests(unittest.TestCase):
    def setUp(self):
        self.repo = _Repo()
        self.repo.add(
            "alpha.tool",
            name="Alpha Tool",
            summary="An alpha development tool.",
            stages=["building"], tags=["alpha"],
            conflicts_with=["beta.tool"],
        )
        self.repo.add(
            "beta.tool",
            name="Beta Tool",
            summary="A beta development tool.",
            stages=["building"], tags=["beta"],
            conflicts_with=["alpha.tool"],
        )
        self.registry = self.repo.registry()

    def tearDown(self):
        self.repo.cleanup()

    def test_conflict_between_selected_skills_is_surfaced(self):
        planner = GraphPlanner(self.registry)
        result = planner.plan("alpha beta development tool")
        ids = {s.skill_id for s in result.steps}
        if {"alpha.tool", "beta.tool"} <= ids:
            self.assertTrue(any(c["type"] == "conflicts_with" for c in result.conflicts))
            self.assertTrue(any("conflict" in w.lower() for w in result.warnings))


if __name__ == "__main__":
    unittest.main()
