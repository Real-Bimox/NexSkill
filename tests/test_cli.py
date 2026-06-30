"""Lane B - CLI tests.

Verifies the public command family end to end via ``python -m nexskill``:
``--help``, ``init`` (with --force and idempotency), ``plan``/``check``/
``closeout`` with ``--json``, and the JSON envelope contract.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(args, cwd, env):
    env = {**env, "PYTHONPATH": str(REPO_ROOT / "src")}
    proc = subprocess.run(
        [sys.executable, "-m", "nexskill", *args],
        cwd=cwd, env=env, capture_output=True, text=True, check=False,
    )
    return proc


class CliSmokeTests(unittest.TestCase):
    def test_help_works(self):
        env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
        proc = subprocess.run(
            [sys.executable, "-m", "nexskill", "--help"],
            cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("nexskill", proc.stdout.lower())
        self.assertIn("init", proc.stdout)
        self.assertIn("plan", proc.stdout)


class CliInitPlanCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, args):
        return _run(args, cwd=str(self.repo), env=os.environ)

    def test_init_creates_config_and_seeds_skills(self):
        proc = self._run(["init", "--repo", ".", "--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["op"], "init")
        self.assertTrue((self.repo / ".nexskill" / "config.json").exists())
        self.assertTrue(len(payload["result"]["skills_seeded"]) >= 1)
        # seed skills materialized on disk
        self.assertTrue((self.repo / ".nexskill" / "skills").is_dir())

    def test_init_idempotent_without_force_errors(self):
        self._run(["init", "--repo", "."])
        proc = self._run(["init", "--repo", ".", "--json"])
        self.assertNotEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "CONFIG_EXISTS")

    def test_init_force_overwrites(self):
        self._run(["init", "--repo", "."])
        proc = self._run(["init", "--repo", ".", "--force", "--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(json.loads(proc.stdout)["ok"])

    def test_plan_returns_json_envelope_with_steps(self):
        self._run(["init", "--repo", "."])
        proc = self._run(["plan", "plan and build a development change", "--repo", ".", "--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["op"], "plan")
        self.assertEqual(payload["schema_version"], "nexskill.v1")
        self.assertGreaterEqual(len(payload["result"]["steps"]), 1)
        self.assertTrue((self.repo / ".nexskill" / "reports" / "latest.json").exists())

    def test_check_passes_on_fresh_repo(self):
        self._run(["init", "--repo", "."])
        proc = self._run(["check", "--repo", ".", "--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["status"], "passed")

    def test_closeout_writes_evidence_and_report(self):
        self._run(["init", "--repo", "."])
        proc = self._run(["closeout", "--repo", ".", "--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["op"], "closeout")
        self.assertTrue((self.repo / ".nexskill" / "evidence.jsonl").exists())
        self.assertTrue((self.repo / ".nexskill" / "reports" / "latest.md").exists())

    def test_check_without_init_returns_config_missing_envelope(self):
        proc = self._run(["check", "--repo", ".", "--json"])
        self.assertNotEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "CONFIG_MISSING")

    def test_json_error_path_emits_clean_envelope_without_traceback(self):
        # A NexSkillError in --json mode must produce only the error envelope on
        # stdout and exit 1, never a leaked Python traceback on stderr.
        proc = self._run(["skill", "scaffold", "not a valid id!!", "--repo", ".", "--json"])
        self.assertEqual(proc.returncode, 1, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["op"], "skill-scaffold")
        self.assertNotIn("Traceback", proc.stderr)
        self.assertNotIn("_Exit", proc.stderr)


class CliSkillSubcommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        _run(["init", "--repo", "."], cwd=str(self.repo), env=os.environ)

    def tearDown(self):
        self.tmp.cleanup()

    def test_skill_list(self):
        proc = _run(["skill", "list", "--repo", ".", "--json"], cwd=str(self.repo), env=os.environ)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertGreaterEqual(payload["result"]["loaded"], 1)

    def test_skill_validate(self):
        proc = _run(["skill", "validate", "--repo", ".", "--json"], cwd=str(self.repo), env=os.environ)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["result"]["valid"])


class CliHumanOutputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        _run(["init", "--repo", "."], cwd=str(self.repo), env=os.environ)

    def tearDown(self):
        self.tmp.cleanup()

    def test_human_output_uses_product_name(self):
        proc = _run(["check", "--repo", "."], cwd=str(self.repo), env=os.environ)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("NexSkill", proc.stdout)


if __name__ == "__main__":
    unittest.main()
