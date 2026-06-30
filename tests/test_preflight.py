"""Lane isolation preflight tests.

Drive a real temporary git repository through the preflight to confirm each
verdict: clean lane, branch mismatch, tracked changes, unexpected untracked
files (and allow-listing), missing base, not-a-repo, and the JSON envelope.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from nexskill import preflight

REPO_SRC = str(Path(__file__).resolve().parents[1] / "src")


class _GitRepo:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._git("init", "-b", "main")
        (self.root / "file.txt").write_text("hello\n", encoding="utf-8")
        self._git("add", "file.txt")
        self._commit("initial commit")

    def _git(self, *args) -> str:
        proc = subprocess.run(
            ["git", "-C", str(self.root),
             "-c", "user.email=lane@nexskill.test", "-c", "user.name=NexSkill Lane",
             "-c", "commit.gpgsign=false", *args],
            capture_output=True, text=True, check=False,
        )
        return proc.stdout.strip()

    def _commit(self, message: str) -> str:
        self._git("commit", "-m", message, "--no-gpg-sign")
        return self._git("rev-parse", "HEAD")

    def cleanup(self):
        self.tmp.cleanup()


class PreflightCleanTests(unittest.TestCase):
    def setUp(self):
        self.repo = _GitRepo()

    def tearDown(self):
        self.repo.cleanup()

    def test_clean_lane_on_expected_branch_passes(self):
        result = preflight.run_preflight(
            str(self.repo.root), expected_branch="main", expected_base="main",
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.failures, [])
        self.assertEqual(result.branch, "main")
        self.assertTrue(result.branch_matches)
        self.assertTrue(result.base_is_ancestor)

    def test_reports_core_state(self):
        result = preflight.run_preflight(str(self.repo.root))
        self.assertTrue(result.worktree)
        self.assertEqual(result.branch, "main")
        self.assertEqual(len(result.head), 40)
        # no upstream configured in a bare local repo
        self.assertIsNone(result.upstream)

    def test_envelope_shape(self):
        env = preflight.run_preflight(str(self.repo.root), expected_branch="main").to_envelope()
        self.assertTrue(env["ok"])
        self.assertEqual(env["op"], "preflight")
        self.assertEqual(env["schema_version"], "nexskill.v1")
        for key in ("worktree", "branch", "head", "upstream", "branch_matches",
                    "base_is_ancestor", "dirty_tracked", "untracked",
                    "unexpected_untracked", "failures", "summary"):
            self.assertIn(key, env["result"], msg=key)


class PreflightFailureTests(unittest.TestCase):
    def setUp(self):
        self.repo = _GitRepo()

    def tearDown(self):
        self.repo.cleanup()

    def _codes(self, result):
        return {f.code for f in result.failures}

    def test_branch_mismatch_fails(self):
        result = preflight.run_preflight(str(self.repo.root), expected_branch="some-lane")
        self.assertFalse(result.ok)
        self.assertIn("BRANCH_MISMATCH", self._codes(result))

    def test_tracked_changes_fail(self):
        (self.repo.root / "file.txt").write_text("changed\n", encoding="utf-8")
        result = preflight.run_preflight(str(self.repo.root), expected_branch="main")
        self.assertFalse(result.ok)
        self.assertIn("TRACKED_CHANGES", self._codes(result))
        self.assertIn("file.txt", result.dirty_tracked)

    def test_unexpected_untracked_fails_then_allowlist_clears(self):
        (self.repo.root / "stray.tmp").write_text("x", encoding="utf-8")
        result = preflight.run_preflight(str(self.repo.root), expected_branch="main")
        self.assertFalse(result.ok)
        self.assertIn("UNEXPECTED_UNTRACKED", self._codes(result))
        self.assertIn("stray.tmp", result.unexpected_untracked)
        # allow-listing the path clears the failure but still reports it as untracked
        allowed = preflight.run_preflight(
            str(self.repo.root), expected_branch="main", allow_untracked=["stray.tmp"],
        )
        self.assertTrue(allowed.ok)
        self.assertIn("stray.tmp", allowed.untracked)
        self.assertEqual(allowed.unexpected_untracked, [])

    def test_allowlist_glob_and_prefix(self):
        (self.repo.root / "docs").mkdir()
        (self.repo.root / "docs" / "sdk").mkdir()
        (self.repo.root / "docs" / "sdk" / "a.md").write_text("x", encoding="utf-8")
        result = preflight.run_preflight(
            str(self.repo.root), allow_untracked=["docs/sdk"],
        )
        self.assertEqual(result.unexpected_untracked, [])

    def test_missing_base_fails(self):
        # Create a sibling branch with a commit that is NOT in main's history.
        self.repo._git("checkout", "-b", "sibling")
        (self.repo.root / "other.txt").write_text("y\n", encoding="utf-8")
        self.repo._git("add", "other.txt")
        sibling_head = self.repo._commit("sibling commit")
        self.repo._git("checkout", "main")
        result = preflight.run_preflight(
            str(self.repo.root), expected_branch="main", expected_base=sibling_head,
        )
        self.assertFalse(result.ok)
        self.assertIn("MISSING_BASE", self._codes(result))
        self.assertFalse(result.base_is_ancestor)

    def test_not_a_git_repo_fails_clearly(self):
        with tempfile.TemporaryDirectory() as plain:
            result = preflight.run_preflight(plain, expected_branch="main")
            self.assertFalse(result.ok)
            self.assertEqual([f.code for f in result.failures], ["NOT_A_GIT_REPO"])


class PreflightCliEntryTests(unittest.TestCase):
    def setUp(self):
        self.repo = _GitRepo()

    def tearDown(self):
        self.repo.cleanup()

    def test_main_exit_zero_on_pass(self):
        rc = preflight.main(["--repo", str(self.repo.root), "--expected-branch", "main"])
        self.assertEqual(rc, 0)

    def test_main_exit_one_on_fail(self):
        rc = preflight.main(["--repo", str(self.repo.root), "--expected-branch", "nope", "--json"])
        self.assertEqual(rc, 1)

    def test_nexskill_preflight_subcommand_json(self):
        env = {**os.environ, "PYTHONPATH": REPO_SRC}
        proc = subprocess.run(
            [sys.executable, "-m", "nexskill", "preflight",
             "--repo", str(self.repo.root), "--expected-branch", "main", "--json"],
            capture_output=True, text=True, check=False, env=env,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["op"], "preflight")
        self.assertEqual(payload["result"]["branch"], "main")


if __name__ == "__main__":
    unittest.main()
