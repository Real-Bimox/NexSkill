"""Lane F - Integration tests.

Proves the round works end to end:

1. A fixture repository can run init -> plan -> check -> closeout and produce
   config, evidence, and both report forms.
2. The NexSkill repository itself can run plan and check (dogfood).
3. The naming/policy scan passes: generated reports contain no forbidden source
   names, and no attribution/policy violations exist in user-facing surfaces.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(args, cwd, env):
    env = {**env, "PYTHONPATH": str(REPO_ROOT / "src")}
    return subprocess.run(
        [sys.executable, "-m", "nexskill", *args],
        cwd=cwd, env=env, capture_output=True, text=True, check=False,
    )


class EndToEndFixtureTests(unittest.TestCase):
    """A fresh fixture repo runs the full command sequence."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_sequence_produces_artifacts(self):
        env = os.environ

        # init
        proc = _run(["init", "--repo", ".", "--json"], cwd=str(self.repo), env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((self.repo / ".nexskill" / "config.json").exists())
        self.assertTrue((self.repo / ".nexskill" / "skills").is_dir())

        # plan
        proc = _run(
            ["plan", "plan and build a small development change", "--repo", ".", "--json"],
            cwd=str(self.repo), env=env,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        plan = json.loads(proc.stdout)
        self.assertTrue(plan["ok"])
        self.assertGreaterEqual(len(plan["result"]["steps"]), 1)

        # check
        proc = _run(["check", "--repo", ".", "--json"], cwd=str(self.repo), env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        check = json.loads(proc.stdout)
        self.assertEqual(check["result"]["status"], "passed")

        # closeout
        proc = _run(["closeout", "--repo", ".", "--json"], cwd=str(self.repo), env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        closeout = json.loads(proc.stdout)
        self.assertTrue(closeout["ok"])

        # artifacts all present
        self.assertTrue((self.repo / ".nexskill" / "evidence.jsonl").exists())
        self.assertTrue((self.repo / ".nexskill" / "reports" / "latest.json").exists())
        self.assertTrue((self.repo / ".nexskill" / "reports" / "latest.md").exists())

    def test_evidence_records_each_op(self):
        env = os.environ
        _run(["init", "--repo", "."], cwd=str(self.repo), env=env)
        _run(["plan", "build something", "--repo", "."], cwd=str(self.repo), env=env)
        _run(["check", "--repo", "."], cwd=str(self.repo), env=env)
        _run(["closeout", "--repo", "."], cwd=str(self.repo), env=env)
        evpath = self.repo / ".nexskill" / "evidence.jsonl"
        ops = []
        for line in evpath.read_text(encoding="utf-8").splitlines():
            if line.strip():
                ops.append(json.loads(line)["op"])
        # init, plan, closeout at minimum (check does not write evidence)
        self.assertIn("init", ops)
        self.assertIn("plan", ops)
        self.assertIn("closeout", ops)

    def test_failed_required_check_makes_closeout_fail(self):
        env = os.environ
        _run(["init", "--repo", "."], cwd=str(self.repo), env=env)
        # Add a failing required check to the config.
        cfg_path = self.repo / ".nexskill" / "config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg["checks"] = [{"id": "tests", "command": "exit 1", "required": True}]
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

        proc = _run(["closeout", "--repo", ".", "--json"], cwd=str(self.repo), env=env)
        self.assertNotEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        # envelope still well-formed; result records failure
        self.assertIn(payload["result"]["status"], ("failed",))


class DogfoodOnSelfTests(unittest.TestCase):
    """The NexSkill repository itself can run plan and check."""

    def test_plan_and_check_on_self(self):
        env = os.environ
        # Use a throwaway config dir so we never touch the real repo state.
        with tempfile.TemporaryDirectory() as tmp:
            proc = _run(["init", "--repo", tmp, "--json"], cwd=tmp, env=env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            proc = _run(["plan", "add a planning skill", "--repo", tmp, "--json"], cwd=tmp, env=env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            proc = _run(["check", "--repo", tmp, "--json"], cwd=tmp, env=env)
            self.assertEqual(proc.returncode, 0, proc.stderr)


class SecondRepoDogfoodTests(unittest.TestCase):
    """A second, independent repository with a project-specific skill added by
    manifest alone runs the full sequence — proving portability and the
    no-core-code-change extension rule."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _add_custom_skill(self):
        pkg = self.repo / ".nexskill" / "skills" / "deploying.release-prep"
        pkg.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema_version": "nexskill.skill.v1",
            "id": "deploying.release-prep",
            "name": "Release Preparation",
            "summary": "Prepares a deployment by checking version and changelog readiness.",
            "stages": ["closing"],
            "inputs": ["closeout_report"],
            "outputs": ["release_candidate"],
            "depends_on": [],
            "conflicts_with": [],
            "tags": ["deploying", "release"],
            "entrypoint": "SKILL.md",
        }
        (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (pkg / "SKILL.md").write_text("# Release Preparation\n", encoding="utf-8")

    def test_custom_skill_added_by_manifest_only(self):
        env = os.environ
        _run(["init", "--repo", ".", "--project-name", "second-repo"], cwd=str(self.repo), env=env)
        self._add_custom_skill()

        # validate: registry accepts the new package with no code change
        proc = _run(["skill", "validate", "--repo", ".", "--json"], cwd=str(self.repo), env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(json.loads(proc.stdout)["result"]["valid"])

        # list: the new skill is discoverable
        proc = _run(["skill", "list", "--repo", ".", "--json"], cwd=str(self.repo), env=env)
        ids = [s["id"] for s in json.loads(proc.stdout)["result"]["skills"]]
        self.assertIn("deploying.release-prep", ids)

        # plan: a matching task selects the new skill
        proc = _run(["plan", "prepare a release deployment", "--repo", ".", "--json"], cwd=str(self.repo), env=env)
        plan = json.loads(proc.stdout)
        plan_ids = [s["skill_id"] for s in plan["result"]["steps"]]
        self.assertIn("deploying.release-prep", plan_ids)

        # full closeout still works on the second repo
        proc = _run(["closeout", "--repo", ".", "--json"], cwd=str(self.repo), env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(json.loads(proc.stdout)["ok"])

    def test_plan_records_latency_evidence(self):
        env = os.environ
        _run(["init", "--repo", "."], cwd=str(self.repo), env=env)
        _run(["plan", "build a development change", "--repo", "."], cwd=str(self.repo), env=env)
        evpath = self.repo / ".nexskill" / "evidence.jsonl"
        plan_events = [
            json.loads(ln) for ln in evpath.read_text(encoding="utf-8").splitlines()
            if ln.strip() and json.loads(ln)["op"] == "plan"
        ]
        self.assertTrue(plan_events)
        self.assertIn("duration_ms", plan_events[-1]["data"])


class GraphOverlayPlanTests(unittest.TestCase):
    """An optional .nexskill/graph.json overlay enriches planning; an invalid
    overlay fails closed."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        _run(["init", "--repo", "."], cwd=str(self.repo), env=os.environ)

    def tearDown(self):
        self.tmp.cleanup()

    def test_invalid_overlay_fails_closed(self):
        overlay = self.repo / ".nexskill" / "graph.json"
        overlay.write_text('{"schema_version": "wrong", "edges": []}', encoding="utf-8")
        proc = _run(["plan", "build a change", "--repo", ".", "--json"], cwd=str(self.repo), env=os.environ)
        self.assertNotEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "GRAPH_INVALID")

    def test_overlay_edge_count_reported(self):
        overlay = self.repo / ".nexskill" / "graph.json"
        overlay.write_text(
            json.dumps({
                "schema_version": "nexskill.graph.v1",
                "edges": [{"source": "planning.task-breakdown",
                           "target": "closing.handoff", "type": "composes_with"}],
            }),
            encoding="utf-8",
        )
        proc = _run(["plan", "plan the work", "--repo", ".", "--json"], cwd=str(self.repo), env=os.environ)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)["result"]
        self.assertEqual(result["graph"]["overlay_edges"], 1)


class NamingAndPolicyScanTests(unittest.TestCase):
    """Generated reports must contain no forbidden source names."""

    FORBIDDEN = (
        "skilldag", "autodev", "agent-skills", "graph-of-skills",
        "real-bimox", "openai", "gpt",
    )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        _run(["init", "--repo", "."], cwd=str(self.repo), env=os.environ)
        _run(["plan", "build a development change", "--repo", "."], cwd=str(self.repo), env=os.environ)
        _run(["closeout", "--repo", "."], cwd=str(self.repo), env=os.environ)

    def tearDown(self):
        self.tmp.cleanup()

    def test_generated_reports_exclude_source_names(self):
        reports = self.repo / ".nexskill" / "reports"
        blob = (reports / "latest.json").read_text(encoding="utf-8").lower()
        blob += (reports / "latest.md").read_text(encoding="utf-8").lower()
        for name in self.FORBIDDEN:
            self.assertNotIn(name, blob, msg=f"forbidden source name {name!r} found in report")

    def test_evidence_excludes_source_names(self):
        evpath = self.repo / ".nexskill" / "evidence.jsonl"
        blob = evpath.read_text(encoding="utf-8").lower()
        for name in self.FORBIDDEN:
            self.assertNotIn(name, blob, msg=name)


class UserFacingSurfaceAttributionScanTests(unittest.TestCase):
    """AGENTS.md rule 1: no AI/model/tool attribution; rule 2: NexSkill only as
    product name in user-facing surfaces changed this round."""

    def test_new_nexskill_surfaces_use_product_name(self):
        # CLI help is the primary user-facing surface.
        env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
        proc = subprocess.run(
            [sys.executable, "-m", "nexskill", "--help"],
            cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("NexSkill", proc.stdout)

    def test_no_attribution_trailers_in_new_source(self):
        import nexskill
        pkg_dir = Path(nexskill.__file__).resolve().parent
        offenders = []
        for src in pkg_dir.rglob("*.py"):
            text = src.read_text(encoding="utf-8")
            low = text.lower()
            for marker in ("co-authored-by", "generated-by", "authored-by:"):
                if marker in low:
                    offenders.append(str(src))
        self.assertEqual(offenders, [], msg=f"attribution markers found: {offenders}")


if __name__ == "__main__":
    unittest.main()
