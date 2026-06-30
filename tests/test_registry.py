"""Lane C - Skill Registry tests.

Discovery, validation, deterministic indexing, and metadata-only lookups.
Fixtures cover the required plan scenarios: duplicate id, missing field, invalid
entrypoint, deterministic sort, and bounded load.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from nexskill.contracts import SKILL_SCHEMA_VERSION, SkillSource
from nexskill.registry import SkillRegistry


def _manifest(package_id, **overrides):
    base = {
        "schema_version": SKILL_SCHEMA_VERSION,
        "id": package_id,
        "name": package_id.replace(".", " ").replace("-", " ").title(),
        "summary": f"Skill {package_id}.",
        "stages": ["planning"],
        "inputs": [],
        "outputs": ["plan"],
        "depends_on": [],
        "conflicts_with": [],
        "tags": ["dev"],
        "entrypoint": "SKILL.md",
    }
    base.update(overrides)
    return base


class _TempRepo:
    def __init__(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def add_skill(self, package_id, manifest=None, *, body="# body\n", entrypoint="SKILL.md", dir_name=None, **overrides):
        d = self.root / ".nexskill" / "skills" / (dir_name or package_id)
        d.mkdir(parents=True, exist_ok=True)
        merged = manifest if manifest is not None else _manifest(package_id)
        if overrides:
            merged = {**merged, **overrides}
            if "entrypoint" not in overrides:
                merged["entrypoint"] = entrypoint
        d.mkdir(parents=True, exist_ok=True)
        (d / entrypoint).write_text(body, encoding="utf-8")
        (d / "manifest.json").write_text(json.dumps(merged), encoding="utf-8")
        return d

    def add_bad_skill(self, dir_name, *, manifest_text=None):
        d = self.root / ".nexskill" / "skills" / dir_name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text("# x\n", encoding="utf-8")
        if manifest_text is not None:
            (d / "manifest.json").write_text(manifest_text, encoding="utf-8")
        return d

    def cleanup(self):
        self.tmp.cleanup()

    def load(self):
        sources = [SkillSource(type="local", path=".nexskill/skills")]
        return SkillRegistry.load(sources, self.root)


class RegistryDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.repo = _TempRepo()

    def tearDown(self):
        self.repo.cleanup()

    def test_loads_valid_packages_and_reports(self):
        self.repo.add_skill("planning.task-breakdown", stages=["planning"])
        self.repo.add_skill("building.impl", stages=["building"])
        registry, report = self.repo.load()
        self.assertEqual(registry.ids(), ["building.impl", "planning.task-breakdown"])
        self.assertEqual(sorted(report.loaded), ["building.impl", "planning.task-breakdown"])
        self.assertEqual(report.skipped, [])
        self.assertTrue(report.ok)

    def test_empty_and_missing_sources_tolerated(self):
        # Source dir does not exist yet.
        registry, report = self.repo.load()
        self.assertEqual(len(registry), 0)
        self.assertEqual(report.loaded, [])
        self.assertEqual(report.skipped, [])

    def test_package_without_manifest_is_skipped(self):
        self.repo.add_skill("good.one")
        self.repo.add_bad_skill("no-manifest")  # SKILL.md only, no manifest.json
        registry, report = self.repo.load()
        self.assertEqual(registry.ids(), ["good.one"])
        codes = [s["code"] for s in report.skipped]
        self.assertIn("MANIFEST_MISSING", codes)

    def test_duplicate_id_is_skipped(self):
        self.repo.add_skill("dup.id", dir_name="dup-a")
        self.repo.add_skill("dup.id", dir_name="dup-b")
        registry, report = self.repo.load()
        self.assertEqual(len(registry), 1)
        codes = [s["code"] for s in report.skipped]
        self.assertIn("DUPLICATE_ID", codes)

    def test_missing_required_field_skipped(self):
        bad = _manifest("broken.missing")
        bad.pop("summary")
        self.repo.add_bad_skill("broken-missing", manifest_text=json.dumps(bad))
        registry, report = self.repo.load()
        self.assertEqual(registry.ids(), [])
        self.assertEqual(report.skipped[0]["code"], "SKILL_INVALID")

    def test_invalid_entrypoint_skipped(self):
        manifest = _manifest("broken.entrypoint", entrypoint="MISSING.md")
        self.repo.add_bad_skill("broken-entrypoint", manifest_text=json.dumps(manifest))
        registry, report = self.repo.load()
        self.assertEqual(registry.ids(), [])
        self.assertEqual(report.skipped[0]["code"], "SKILL_INVALID")

    def test_malformed_json_skipped(self):
        self.repo.add_bad_skill("broken-json", manifest_text="{ not json")
        registry, report = self.repo.load()
        self.assertEqual(registry.ids(), [])
        self.assertEqual(report.skipped[0]["code"], "SKILL_INVALID")


class RegistryIndexTests(unittest.TestCase):
    def setUp(self):
        self.repo = _TempRepo()
        self.repo.add_skill(
            "planning.task-breakdown",
            stages=["planning"], outputs=["implementation_plan"],
            tags=["dev", "planning"], depends_on=[],
        )
        self.repo.add_skill(
            "building.implementation",
            stages=["building"], outputs=["code_change"],
            tags=["dev", "building"], depends_on=["planning.task-breakdown"],
        )
        self.repo.add_skill(
            "verifying.testing",
            stages=["verifying"], outputs=["test_evidence"],
            tags=["dev", "testing"], depends_on=["building.implementation"],
        )
        self.registry, _ = self.repo.load()

    def tearDown(self):
        self.repo.cleanup()

    def test_deterministic_sort(self):
        # ids() is sorted regardless of insertion order / filesystem order.
        ids = self.registry.ids()
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(ids[0], "building.implementation")

    def test_index_is_metadata_only(self):
        idx = self.registry.index()
        blob = json.dumps(idx)
        self.assertNotIn("# body", blob)  # skill body must not leak into the index
        self.assertEqual(len(idx), 3)
        self.assertIn("stages", idx[0])

    def test_lookup_by_stage(self):
        ids = [s.id for s in self.registry.by_stage("building")]
        self.assertEqual(ids, ["building.implementation"])

    def test_lookup_by_tag(self):
        ids = [s.id for s in self.registry.by_tag("testing")]
        self.assertEqual(ids, ["verifying.testing"])

    def test_lookup_by_output(self):
        ids = [s.id for s in self.registry.by_output("test_evidence")]
        self.assertEqual(ids, ["verifying.testing"])

    def test_require_missing_raises(self):
        from nexskill.contracts import NexSkillError

        with self.assertRaises(NexSkillError) as ctx:
            self.registry.require("nope")
        self.assertEqual(ctx.exception.code, "SKILL_NOT_FOUND")

    def test_depends_on_resolved(self):
        self.assertEqual(
            self.registry.depends_on("building.implementation"),
            ["planning.task-breakdown"],
        )

    def test_body_available_only_via_explicit_call(self):
        skill = self.registry.get("planning.task-breakdown")
        self.assertIn("# body", skill.body())  # explicit, not via index/plan


class BoundedLoadTests(unittest.TestCase):
    def test_large_corpus_indexes_without_bodies(self):
        repo = _TempRepo()
        for i in range(60):
            repo.add_skill(f"skill.{i:03d}", tags=[f"tag{i % 4}"])
        registry, report = repo.load()
        repo.cleanup()
        self.assertEqual(len(registry), 60)
        self.assertEqual(len(report.loaded), 60)
        # index() over 60 skills stays small and body-free.
        idx = registry.index()
        self.assertEqual(len(idx), 60)
        self.assertNotIn("# body", json.dumps(idx))


if __name__ == "__main__":
    unittest.main()
