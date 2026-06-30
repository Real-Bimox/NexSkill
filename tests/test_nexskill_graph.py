"""NexSkill skill-graph tests.

Edge validation, overlay loading (fail-closed on invalid), manifest-edge
construction, walkable traversal (conflicts excluded), bounded determinism, and
conflict collection.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from nexskill.contracts import GRAPH_SCHEMA_VERSION, NexSkillError, SKILL_SCHEMA_VERSION, SkillSource
from nexskill.graph import GraphEdge, SkillGraph, load_overlay_edges, overlay_path
from nexskill.registry import SkillRegistry


def _manifest(package_id, **overrides):
    base = {
        "schema_version": SKILL_SCHEMA_VERSION,
        "id": package_id,
        "name": package_id.title(),
        "summary": f"Skill {package_id}.",
        "stages": ["building"],
        "entrypoint": "SKILL.md",
    }
    base.update(overrides)
    return base


class _Repo:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def add(self, package_id, **overrides):
        d = self.root / "skills" / package_id
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text("# body\n", encoding="utf-8")
        (d / "manifest.json").write_text(json.dumps(_manifest(package_id, **overrides)), encoding="utf-8")

    def registry(self):
        reg, _ = SkillRegistry.load([SkillSource(type="local", path="skills")], self.root)
        return reg

    def write_overlay(self, obj):
        p = overlay_path(self.root)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj), encoding="utf-8")

    def cleanup(self):
        self.tmp.cleanup()


class GraphEdgeTests(unittest.TestCase):
    def test_valid_edge(self):
        e = GraphEdge.from_dict({"source": "a.x", "target": "b.y", "type": "composes_with"})
        self.assertEqual((e.source, e.target, e.type), ("a.x", "b.y", "composes_with"))

    def test_invalid_type_rejected(self):
        with self.assertRaises(NexSkillError) as ctx:
            GraphEdge.from_dict({"source": "a", "target": "b", "type": "nope"})
        self.assertEqual(ctx.exception.code, "GRAPH_INVALID")

    def test_missing_field_rejected(self):
        with self.assertRaises(NexSkillError):
            GraphEdge.from_dict({"source": "a", "type": "depends_on"})

    def test_self_loop_rejected(self):
        with self.assertRaises(NexSkillError):
            GraphEdge.from_dict({"source": "a", "target": "a", "type": "depends_on"})


class OverlayLoadingTests(unittest.TestCase):
    def setUp(self):
        self.repo = _Repo()

    def tearDown(self):
        self.repo.cleanup()

    def test_missing_overlay_is_empty(self):
        self.assertEqual(load_overlay_edges(self.repo.root), [])

    def test_valid_overlay_loads(self):
        self.repo.write_overlay(
            {
                "schema_version": GRAPH_SCHEMA_VERSION,
                "edges": [{"source": "a.x", "target": "b.y", "type": "composes_with"}],
            }
        )
        edges = load_overlay_edges(self.repo.root)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].type, "composes_with")

    def test_bad_schema_fails_closed(self):
        self.repo.write_overlay({"schema_version": "wrong", "edges": []})
        with self.assertRaises(NexSkillError) as ctx:
            load_overlay_edges(self.repo.root)
        self.assertEqual(ctx.exception.code, "GRAPH_INVALID")

    def test_bad_json_fails_closed(self):
        p = overlay_path(self.repo.root)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{not json", encoding="utf-8")
        with self.assertRaises(NexSkillError) as ctx:
            load_overlay_edges(self.repo.root)
        self.assertEqual(ctx.exception.code, "GRAPH_INVALID")


class GraphConstructionTests(unittest.TestCase):
    def setUp(self):
        self.repo = _Repo()
        self.repo.add("planning.x", stages=["planning"])
        self.repo.add("building.y", depends_on=["planning.x"], conflicts_with=["other.z"])
        self.repo.add("other.z", conflicts_with=["building.y"])
        self.registry = self.repo.registry()

    def tearDown(self):
        self.repo.cleanup()

    def test_manifest_depends_on_is_directed(self):
        g = SkillGraph.from_registry(self.registry)
        # building.y -> planning.x via depends_on
        self.assertIn(("planning.x", "depends_on"), g.neighbors("building.y"))
        # not the reverse
        self.assertNotIn(("building.y", "depends_on"), g.neighbors("planning.x"))

    def test_conflicts_are_symmetric_and_not_walkable(self):
        g = SkillGraph.from_registry(self.registry)
        self.assertIn("other.z", g.conflicts("building.y"))
        self.assertIn("building.y", g.conflicts("other.z"))
        # conflicts_with is never a walkable neighbor
        self.assertNotIn(
            "other.z", [n for (n, _t) in g.walkable_neighbors("building.y")]
        )

    def test_overlay_edges_merge_in(self):
        edges = [GraphEdge("planning.x", "building.y", "composes_with")]
        g = SkillGraph.from_registry(self.registry, edges)
        names = [n for (n, _t) in g.walkable_neighbors("planning.x")]
        self.assertIn("building.y", names)  # symmetric composes_with

    def test_bounded_expand_is_bounded_and_deterministic(self):
        edges = [GraphEdge("planning.x", "building.y", "composes_with")]
        g = SkillGraph.from_registry(self.registry, edges)
        a = g.bounded_expand(["planning.x"], max_nodes=2)
        b = g.bounded_expand(["planning.x"], max_nodes=2)
        self.assertEqual(a, b)
        self.assertLessEqual(len(a), 2)
        self.assertEqual(a[0]["id"], "planning.x")

    def test_collect_conflicts_only_within_set(self):
        g = SkillGraph.from_registry(self.registry)
        conflicts = g.collect_conflicts(["building.y", "other.z"])
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["type"], "conflicts_with")
        # if only one side is selected, no conflict surfaced
        self.assertEqual(g.collect_conflicts(["building.y"]), [])


if __name__ == "__main__":
    unittest.main()
