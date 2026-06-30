"""Lane G - Skill pack SDK tests.

Covers the round 2b skill pack SDK surface:

1. Resolution helpers (id derivation, title-casing, option validation).
2. Template rendering and the generated manifest shape.
3. The ``scaffold_skill`` function: it writes a loadable package, refuses to
   overwrite without ``--force``, and overwrites with it.
4. The ``nexskill skill scaffold`` CLI command end to end (subprocess, JSON
   envelope, human output, error codes).
5. Fixture-driven registry validation against the static fixtures in
   ``tests/fixtures/skill_packs/`` (valid load + SKILL_INVALID /
   MANIFEST_MISSING / DUPLICATE_ID).
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
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "skill_packs"

from nexskill import scaffold  # noqa: E402
from nexskill.contracts import NexSkillError, SkillManifest  # noqa: E402
from nexskill.registry import SkillRegistry  # noqa: E402
from nexskill.contracts import SkillSource  # noqa: E402


def _run(args, cwd, env):
    env = {**env, "PYTHONPATH": str(REPO_ROOT / "src")}
    return subprocess.run(
        [sys.executable, "-m", "nexskill", *args],
        cwd=cwd, env=env, capture_output=True, text=True, check=False,
    )


class _TempRepo:
    """A throwaway repo directory with an initialized NexSkill project."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        env = os.environ
        proc = _run(["init", "--repo", ".", "--json"], cwd=str(self.root), env=env)
        assert proc.returncode == 0, proc.stderr

    def cleanup(self):
        self.tmp.cleanup()


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------


class ResolveOptionsTests(unittest.TestCase):
    """``resolve_options`` validates and defaults scaffold inputs."""

    def test_defaults_id_and_name_from_positional(self):
        opts = scaffold.resolve_options("reviewing.checklist")
        self.assertEqual(opts.id, "reviewing.checklist")
        # Title-casing splits on the dot: "Reviewing Checklist".
        self.assertEqual(opts.name, "Reviewing Checklist")
        self.assertEqual(opts.stage, scaffold.DEFAULT_STAGE)
        self.assertEqual(opts.summary, scaffold.DEFAULT_SUMMARY)

    def test_explicit_overrides_win(self):
        opts = scaffold.resolve_options(
            "reviewing.checklist",
            id="reviewing.deep-check",
            name="Deep Check",
            summary="A deeper review.",
            stage="verifying",
        )
        self.assertEqual(opts.id, "reviewing.deep-check")
        self.assertEqual(opts.name, "Deep Check")
        self.assertEqual(opts.summary, "A deeper review.")
        self.assertEqual(opts.stage, "verifying")

    def test_empty_name_rejected(self):
        with self.assertRaises(NexSkillError) as ctx:
            scaffold.resolve_options("   ")
        self.assertEqual(ctx.exception.code, "SCAFFOLD_INVALID_NAME")

    def test_invalid_id_rejected(self):
        with self.assertRaises(NexSkillError) as ctx:
            scaffold.resolve_options("ok", id="Bad Uppercase")
        self.assertEqual(ctx.exception.code, "SCAFFOLD_INVALID_ID")

    def test_derive_skill_id_squeezes_punctuation(self):
        self.assertEqual(scaffold.derive_skill_id("Review Checklist!"), "review.checklist")
        self.assertEqual(scaffold.derive_skill_id("a---b"), "a.b")
        self.assertEqual(scaffold.derive_skill_id("   "), "")

    def test_title_case_name_handles_separators(self):
        self.assertEqual(scaffold.title_case_name("reviewing.checklist"), "Reviewing Checklist")
        self.assertEqual(scaffold.title_case_name("review-check"), "Review Check")
        self.assertEqual(scaffold.title_case_name(""), "")


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


class RenderTests(unittest.TestCase):
    """``render_text`` / ``render_manifest`` substitute tokens and parse JSON."""

    def test_render_text_substitutes_known_tokens(self):
        out = scaffold.render_text(
            "id=${SKILL_ID} stage=${SKILL_STAGE}",
            {"SKILL_ID": "x.y", "SKILL_STAGE": "verifying"},
        )
        self.assertEqual(out, "id=x.y stage=verifying")

    def test_render_text_leaves_unknown_tokens_intact(self):
        out = scaffold.render_text("keep ${UNKNOWN}", {})
        self.assertEqual(out, "keep ${UNKNOWN}")

    def test_render_manifest_parses_to_dict(self):
        text = '{"id": "${SKILL_ID}", "name": "${SKILL_NAME}"}'
        parsed = scaffold.render_manifest(
            text, {"SKILL_ID": "a.b", "SKILL_NAME": "A B", "SKILL_SUMMARY": "", "SKILL_STAGE": ""}
        )
        self.assertEqual(parsed, {"id": "a.b", "name": "A B"})


# ---------------------------------------------------------------------------
# scaffold_skill core
# ---------------------------------------------------------------------------


class ScaffoldSkillTests(unittest.TestCase):
    """``scaffold_skill`` writes a package the registry can load."""

    def setUp(self):
        self.repo = _TempRepo()

    def tearDown(self):
        self.repo.cleanup()

    def _load_registry(self):
        config_path = self.repo.root / ".nexskill" / "config.json"
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        sources = [SkillSource.from_dict(s) for s in cfg["skill_sources"]]
        return SkillRegistry.load(sources, self.repo.root)

    def test_writes_manifest_and_entrypoint(self):
        result = scaffold.scaffold_skill(
            "reviewing.checklist", self.repo.root,
            name="Review Checklist", summary="Runs a fixed review checklist.",
            stage="verifying",
        )
        pkg = (self.repo.root / ".nexskill" / "skills" / "reviewing.checklist").resolve()
        self.assertEqual(result.package_dir, pkg)
        self.assertEqual(sorted(result.files_written), ["SKILL.md", "manifest.json"])
        manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["id"], "reviewing.checklist")
        self.assertEqual(manifest["name"], "Review Checklist")
        self.assertEqual(manifest["stages"], ["verifying"])
        self.assertEqual(manifest["schema_version"], "nexskill.skill.v1")
        body = (pkg / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Review Checklist", body)

    def test_generated_manifest_validates_through_contract(self):
        # The manifest produced must pass the canonical validator.
        result = scaffold.scaffold_skill(
            "planning.idea", self.repo.root, name="Idea", summary="Capture an idea."
        )
        SkillManifest.from_dict(result.manifest)  # must not raise

    def test_scaffolded_package_loads_in_registry(self):
        scaffold.scaffold_skill(
            "reviewing.checklist", self.repo.root,
            name="Review Checklist", summary="Runs a fixed review checklist.",
            stage="verifying",
        )
        registry, report = self._load_registry()
        self.assertIn("reviewing.checklist", registry.ids())
        self.assertTrue(report.ok, msg=f"registry reported skips: {report.skipped}")

    def test_refuses_overwrite_without_force(self):
        scaffold.scaffold_skill("reviewing.checklist", self.repo.root)
        with self.assertRaises(NexSkillError) as ctx:
            scaffold.scaffold_skill("reviewing.checklist", self.repo.root)
        self.assertEqual(ctx.exception.code, "SCAFFOLD_EXISTS")

    def test_overwrites_with_force(self):
        scaffold.scaffold_skill(
            "reviewing.checklist", self.repo.root, summary="first"
        )
        result = scaffold.scaffold_skill(
            "reviewing.checklist", self.repo.root, summary="second", force=True
        )
        manifest = json.loads(
            (result.package_dir / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["summary"], "second")

    def test_default_skills_dir_used(self):
        # No skills_dir given -> writes under .nexskill/skills/<id>.
        result = scaffold.scaffold_skill("closing.notes", self.repo.root)
        self.assertTrue(result.package_dir.is_relative_to(
            (self.repo.root / ".nexskill" / "skills").resolve()
        ))


# ---------------------------------------------------------------------------
# CLI subprocess
# ---------------------------------------------------------------------------


class ScaffoldCLITests(unittest.TestCase):
    """``nexskill skill scaffold`` end to end via subprocess."""

    def setUp(self):
        self.repo = _TempRepo()

    def tearDown(self):
        self.repo.cleanup()

    def test_json_envelope_success(self):
        proc = _run(
            ["skill", "scaffold", "reviewing.checklist", "--repo", ".",
             "--name", "Review Checklist",
             "--summary", "Runs a fixed review checklist.",
             "--stage", "verifying", "--json"],
            cwd=str(self.repo.root), env=os.environ,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["op"], "skill-scaffold")
        self.assertEqual(payload["schema_version"], "nexskill.v1")
        self.assertEqual(payload["result"]["skill_id"], "reviewing.checklist")
        self.assertEqual(
            payload["result"]["package_dir"],
            ".nexskill/skills/reviewing.checklist",
        )

    def test_human_output_uses_product_name(self):
        proc = _run(
            ["skill", "scaffold", "reviewing.checklist", "--repo", "."],
            cwd=str(self.repo.root), env=os.environ,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("NexSkill", proc.stdout)
        self.assertIn("reviewing.checklist", proc.stdout)

    def test_duplicate_without_force_errors(self):
        _run(
            ["skill", "scaffold", "reviewing.checklist", "--repo", "."],
            cwd=str(self.repo.root), env=os.environ,
        )
        proc = _run(
            ["skill", "scaffold", "reviewing.checklist", "--repo", ".", "--json"],
            cwd=str(self.repo.root), env=os.environ,
        )
        self.assertNotEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "SCAFFOLD_EXISTS")

    def test_force_overwrites(self):
        _run(
            ["skill", "scaffold", "reviewing.checklist", "--repo", ".",
             "--summary", "first"],
            cwd=str(self.repo.root), env=os.environ,
        )
        proc = _run(
            ["skill", "scaffold", "reviewing.checklist", "--repo", ".",
             "--summary", "second", "--force", "--json"],
            cwd=str(self.repo.root), env=os.environ,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["manifest"]["summary"], "second")

    def test_invalid_id_errors(self):
        proc = _run(
            ["skill", "scaffold", "ok", "--id", "Bad Uppercase", "--repo", ".", "--json"],
            cwd=str(self.repo.root), env=os.environ,
        )
        self.assertNotEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["error"]["code"], "SCAFFOLD_INVALID_ID")

    def test_scaffold_then_validate_then_list(self):
        # Full authoring loop: scaffold -> validate passes -> list shows it.
        _run(
            ["skill", "scaffold", "reviewing.checklist", "--repo", ".",
             "--name", "Review Checklist",
             "--summary", "Runs a fixed review checklist.", "--stage", "verifying"],
            cwd=str(self.repo.root), env=os.environ,
        )
        v = _run(["skill", "validate", "--repo", ".", "--json"],
                 cwd=str(self.repo.root), env=os.environ)
        self.assertEqual(v.returncode, 0, v.stderr)
        self.assertTrue(json.loads(v.stdout)["result"]["valid"])

        lst = _run(["skill", "list", "--repo", ".", "--json"],
                   cwd=str(self.repo.root), env=os.environ)
        ids = [s["id"] for s in json.loads(lst.stdout)["result"]["skills"]]
        self.assertIn("reviewing.checklist", ids)


# ---------------------------------------------------------------------------
# Fixture-driven registry validation
# ---------------------------------------------------------------------------


class FixtureRegistryTests(unittest.TestCase):
    """Point a registry at the static fixtures and assert skip codes."""

    def test_valid_fixture_loads(self):
        # A source path points at the *parent* of the package dir; the registry
        # scans its children for manifest.json. Pointing at the fixtures root
        # scans valid.minimal/ (loads) and invalid/ (no manifest -> skipped).
        sources = [SkillSource(type="local", path=".")]
        registry, _report = SkillRegistry.load(sources, FIXTURES)
        self.assertIn("valid.minimal", registry.ids())
        # The valid fixture must itself parse through the canonical contract.
        mf = json.loads((FIXTURES / "valid.minimal" / "manifest.json").read_text("utf-8"))
        SkillManifest.from_dict(mf)

    def test_missing_field_fixture_skipped_skill_invalid(self):
        base = FIXTURES / "invalid"
        sources = [SkillSource(type="local", path=".")]
        _registry, report = SkillRegistry.load(sources, base)
        codes = [s["code"] for s in report.skipped]
        self.assertIn("SKILL_INVALID", codes)

    def test_bad_id_fixture_skipped_skill_invalid(self):
        base = FIXTURES / "invalid"
        sources = [SkillSource(type="local", path=".")]
        _registry, report = SkillRegistry.load(sources, base)
        codes = [s["code"] for s in report.skipped]
        self.assertIn("SKILL_INVALID", codes)

    def test_no_manifest_fixture_skipped_manifest_missing(self):
        base = FIXTURES / "invalid"
        sources = [SkillSource(type="local", path=".")]
        _registry, report = SkillRegistry.load(sources, base)
        codes = [s["code"] for s in report.skipped]
        self.assertIn("MANIFEST_MISSING", codes)

    def test_duplicate_id_across_packages(self):
        # Copy the valid fixture into two sibling dirs with the same id and
        # point a registry at their common parent.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src_a = FIXTURES / "valid.minimal"
            dest_a = root / "pkg-a"
            dest_b = root / "pkg-b"
            self._copy_tree(src_a, dest_a)
            self._copy_tree(src_a, dest_b)  # same id -> duplicate
            sources = [SkillSource(type="local", path=".")]
            _registry, report = SkillRegistry.load(sources, root)
            codes = [s["code"] for s in report.skipped]
            self.assertIn("DUPLICATE_ID", codes)

    @staticmethod
    def _copy_tree(src: Path, dest: Path) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            (dest / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
