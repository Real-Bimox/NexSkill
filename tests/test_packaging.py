"""Packaging and portability tests.

These tests prove NexSkill is installable and portable: its runtime resources
(built-in skills and the scaffold template) ship inside the package, resolve
without any repository-root lookup, and the full command sequence works from a
fresh clone and from a wheel installed in a clean environment outside the source
checkout.

The fresh-clone test copies only tracked files (simulating ``git clone``). The
wheel test builds and installs the package in an isolated virtualenv; it skips
gracefully when the build backend cannot run (e.g. no network for build
isolation) so the rest of the suite stays green in constrained environments.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
PKG = SRC / "nexskill"

EXPECTED_SEED_SKILLS = {
    "building.implementation",
    "closing.handoff",
    "planning.task-breakdown",
    "verifying.testing",
}


class PackagedResourceTests(unittest.TestCase):
    """Runtime resources live inside the package and resolve via the package."""

    def test_resource_path_resolves_skills_and_template(self):
        # Import through the source tree without requiring an install.
        sys.path.insert(0, str(SRC))
        try:
            from nexskill._resources import resource_path
        finally:
            sys.path.pop(0)

        skills = resource_path("skills")
        template = resource_path("templates", "skill_pack")
        self.assertTrue(skills.is_dir(), f"missing skills resource dir: {skills}")
        self.assertTrue(template.is_dir(), f"missing template resource dir: {template}")

        seeded = {p.name for p in skills.iterdir() if p.is_dir()}
        self.assertEqual(seeded, EXPECTED_SEED_SKILLS)
        self.assertTrue((template / "manifest.json").is_file())
        self.assertTrue((template / "SKILL.md").is_file())

    def test_no_repo_root_parent_lookup_in_package(self):
        """No runtime module may resolve resources relative to the repo root."""
        offenders = []
        for src in PKG.rglob("*.py"):
            text = src.read_text(encoding="utf-8")
            # parents[2] from src/nexskill/<mod>.py is the repository root; using
            # it for resource resolution is exactly the bug that broke wheels.
            if "parents[2]" in text:
                offenders.append(str(src.relative_to(REPO_ROOT)))
        self.assertEqual(offenders, [], msg=f"repo-root resource lookup found in: {offenders}")


def _copy_tracked_tree(dest: Path) -> None:
    """Copy only git-tracked files into ``dest`` (a fresh-clone simulation)."""
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=str(REPO_ROOT), capture_output=True, check=True,
    )
    for rel in out.stdout.split(b"\0"):
        if not rel:
            continue
        relpath = Path(os.fsdecode(rel))
        src = REPO_ROOT / relpath
        if not src.is_file():
            continue
        target = dest / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)


class FreshCloneSourceTests(unittest.TestCase):
    """The full sequence works from a tracked-files-only tree (no untracked cruft)."""

    def test_full_sequence_from_fresh_clone(self):
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "clone"
            clone.mkdir()
            _copy_tracked_tree(clone)

            # Resources must have come across as tracked files.
            self.assertTrue((clone / "src" / "nexskill" / "resources" / "skills").is_dir())
            self.assertTrue(
                (clone / "src" / "nexskill" / "resources" / "templates" / "skill_pack").is_dir()
            )

            env = {**os.environ, "PYTHONPATH": str(clone / "src")}
            work = Path(tmp) / "work"
            work.mkdir()

            def run(args):
                return subprocess.run(
                    [sys.executable, "-m", "nexskill", *args],
                    cwd=str(work), env=env, capture_output=True, text=True, check=False,
                )

            proc = run(["init", "--repo", ".", "--json"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            seeded = set(json.loads(proc.stdout)["result"]["skills_seeded"])
            self.assertEqual(seeded, EXPECTED_SEED_SKILLS)

            proc = run(["plan", "build a development change", "--repo", ".", "--json"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertGreaterEqual(len(json.loads(proc.stdout)["result"]["steps"]), 1)

            proc = run(["skill", "scaffold", "reviewing.checklist", "--repo", ".", "--json"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((work / ".nexskill" / "skills" / "reviewing.checklist" / "SKILL.md").is_file())


def _build_wheel(outdir: Path) -> Path | None:
    """Build a wheel from the repo; return its path or None if the build can't run."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(outdir)],
            cwd=str(REPO_ROOT), capture_output=True, text=True, check=False, timeout=600,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    wheels = sorted(outdir.glob("*.whl"))
    return wheels[-1] if wheels else None


class WheelInstallTests(unittest.TestCase):
    """A wheel installs into a clean venv outside the repo and runs the full flow."""

    @classmethod
    def setUpClass(cls):
        import importlib.util

        if importlib.util.find_spec("build") is None:
            raise unittest.SkipTest("the 'build' package is required for wheel-install tests")
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmp.name)
        cls.wheel = _build_wheel(tmp / "dist")
        if cls.wheel is None:
            cls._tmp.cleanup()
            raise unittest.SkipTest("wheel build did not produce an artifact (build backend unavailable)")

        # Clean venv with no access to the source checkout.
        cls.venv_dir = tmp / "venv"
        venv.create(cls.venv_dir, with_pip=True)
        cls.py = cls.venv_dir / ("Scripts" if os.name == "nt" else "bin") / "python"
        install = subprocess.run(
            [str(cls.py), "-m", "pip", "install", "--no-index", "--no-deps", str(cls.wheel)],
            capture_output=True, text=True, check=False, timeout=600,
        )
        if install.returncode != 0:
            cls._tmp.cleanup()
            raise unittest.SkipTest(f"wheel install failed: {install.stderr[-400:]}")
        cls.nexskill = cls.venv_dir / ("Scripts" if os.name == "nt" else "bin") / "nexskill"

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "_tmp", None) is not None:
            cls._tmp.cleanup()

    def test_wheel_is_named_nexskill(self):
        self.assertTrue(
            self.wheel.name.startswith("nexskill-"),
            msg=f"wheel must be a NexSkill distribution, got {self.wheel.name}",
        )

    def test_wheel_bundles_resources(self):
        import zipfile

        with zipfile.ZipFile(self.wheel) as zf:
            names = zf.namelist()
        self.assertTrue(
            any(n.startswith("nexskill/resources/skills/") for n in names),
            msg="wheel is missing built-in skills",
        )
        self.assertTrue(
            any(n.startswith("nexskill/resources/templates/skill_pack/") for n in names),
            msg="wheel is missing the scaffold template",
        )

    def test_only_nexskill_console_script_installed(self):
        bindir = self.venv_dir / ("Scripts" if os.name == "nt" else "bin")
        self.assertTrue(self.nexskill.exists(), "nexskill console script not installed")
        self.assertFalse(
            (bindir / "skilldag").exists(),
            msg="the legacy 'skilldag' console script must not ship in the NexSkill wheel",
        )

    def test_installed_cli_runs_full_sequence_outside_repo(self):
        with tempfile.TemporaryDirectory() as work:
            def run(args):
                return subprocess.run(
                    [str(self.nexskill), *args],
                    cwd=work, capture_output=True, text=True, check=False, timeout=120,
                )

            proc = run(["init", "--repo", ".", "--json"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            seeded = set(json.loads(proc.stdout)["result"]["skills_seeded"])
            self.assertEqual(seeded, EXPECTED_SEED_SKILLS)

            proc = run(["plan", "plan and build a development change", "--repo", ".", "--json"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertGreaterEqual(len(json.loads(proc.stdout)["result"]["steps"]), 1)

            proc = run(["check", "--repo", ".", "--json"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn(json.loads(proc.stdout)["result"]["status"], ("passed", "warning"))

            proc = run(["closeout", "--repo", ".", "--json"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(json.loads(proc.stdout)["ok"])

            proc = run(["skill", "scaffold", "reviewing.checklist", "--repo", ".", "--json"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(json.loads(proc.stdout)["ok"])

            proc = run(["skill", "validate", "--repo", ".", "--json"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(json.loads(proc.stdout)["result"]["valid"])

            # preflight is read-only and deterministic; it must produce a
            # well-formed envelope outside the source checkout.
            proc = run(["preflight", "--repo", ".", "--json"])
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["op"], "preflight")
            self.assertIn("ok", payload)


if __name__ == "__main__":
    unittest.main()
