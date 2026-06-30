"""NexSkill skill graph.

A small, dependency-light, fully deterministic typed-edge graph that the planner
traverses to assemble a bounded skill path. It has two edge sources:

1. **Manifest edges** — every skill's declared ``depends_on`` (directed:
   dependent -> prerequisite) and ``conflicts_with`` (symmetric). These are
   always present and require no extra files.
2. **Overlay edges** — an optional, NexSkill-owned ``.nexskill/graph.json``
   (schema ``nexskill.graph.v1``) that adds the richer relationships
   (``composes_with``, ``specializes``, ``similar_to``, plus more
   ``depends_on`` / ``conflicts_with``) a project learns over time.

With no overlay file, the graph is exactly the manifest dependency structure, so
planning stays byte-for-byte compatible with a manifest-only project. The graph
holds no embeddings, makes no network calls, and needs no API keys: the same
inputs always produce the same traversal.

The planner advises; the graph never claims that a selected path proves work
readiness.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .contracts import (
    GRAPH_EDGE_TYPES,
    GRAPH_SCHEMA_VERSION,
    GRAPH_SYMMETRIC_EDGE_TYPES,
    GRAPH_WALKABLE_EDGE_TYPES,
    NexSkillError,
)
from .registry import SkillRegistry

GRAPH_OVERLAY_FILENAME = "graph.json"


@dataclass(frozen=True)
class GraphEdge:
    """One validated typed edge between two skill ids."""

    source: str
    target: str
    type: str

    @classmethod
    def from_dict(cls, raw: object) -> "GraphEdge":
        if not isinstance(raw, dict):
            raise NexSkillError("GRAPH_INVALID", "graph edge must be a JSON object")
        source = raw.get("source")
        target = raw.get("target")
        etype = raw.get("type")
        for label, val in (("source", source), ("target", target), ("type", etype)):
            if not isinstance(val, str) or not val.strip():
                raise NexSkillError("GRAPH_INVALID", f"graph edge {label} is required")
        if etype not in GRAPH_EDGE_TYPES:
            raise NexSkillError(
                "GRAPH_INVALID",
                f"graph edge type must be one of {GRAPH_EDGE_TYPES}, got {etype!r}",
            )
        if source.strip() == target.strip():
            raise NexSkillError("GRAPH_INVALID", "graph edge source and target must differ")
        return cls(source=source.strip(), target=target.strip(), type=etype)


def overlay_path(repo_root: Path) -> Path:
    return repo_root / ".nexskill" / GRAPH_OVERLAY_FILENAME


def load_overlay_edges(repo_root: Path) -> list[GraphEdge]:
    """Read and validate ``.nexskill/graph.json`` if present.

    A missing overlay is normal and returns an empty list. A present-but-invalid
    overlay fails closed with a stable ``GRAPH_INVALID`` code rather than being
    silently ignored — an inconsistent graph must not quietly degrade planning.
    """
    path = overlay_path(repo_root)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise NexSkillError("GRAPH_INVALID", f"graph.json is not valid JSON: {exc.msg}") from exc
    if not isinstance(raw, dict):
        raise NexSkillError("GRAPH_INVALID", "graph.json must be a JSON object")
    sv = raw.get("schema_version")
    if sv != GRAPH_SCHEMA_VERSION:
        raise NexSkillError(
            "GRAPH_INVALID",
            f"graph schema_version must be {GRAPH_SCHEMA_VERSION}, got {sv!r}",
        )
    edges_raw = raw.get("edges", [])
    if not isinstance(edges_raw, list):
        raise NexSkillError("GRAPH_INVALID", "graph edges must be a list")
    return [GraphEdge.from_dict(e) for e in edges_raw]


class SkillGraph:
    """Deterministic typed-edge graph over skill ids.

    Adjacency is stored as sorted tuples so every traversal — and therefore
    every plan derived from it — is reproducible.
    """

    def __init__(self) -> None:
        # node -> set of (neighbor, edge_type) reachable by following an edge
        # outward in its navigable direction (symmetric edges add both ways).
        self._adj: dict[str, set[tuple[str, str]]] = {}
        self._nodes: set[str] = set()
        self._edge_count = 0

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_registry(
        cls,
        registry: SkillRegistry,
        overlay_edges: Iterable[GraphEdge] | None = None,
    ) -> "SkillGraph":
        graph = cls()
        for skill in registry.all():
            graph._nodes.add(skill.id)
            for dep in skill.manifest.depends_on:
                graph._add_edge(skill.id, dep, "depends_on")
            for conf in skill.manifest.conflicts_with:
                graph._add_edge(skill.id, conf, "conflicts_with")
        for edge in overlay_edges or ():
            graph._add_edge(edge.source, edge.target, edge.type)
        return graph

    def _add_edge(self, source: str, target: str, etype: str) -> None:
        self._nodes.add(source)
        self._nodes.add(target)
        self._adj.setdefault(source, set()).add((target, etype))
        if etype in GRAPH_SYMMETRIC_EDGE_TYPES:
            self._adj.setdefault(target, set()).add((source, etype))
        self._edge_count += 1

    # ------------------------------------------------------------------
    # Queries (deterministic)
    # ------------------------------------------------------------------

    @property
    def edge_count(self) -> int:
        return self._edge_count

    def nodes(self) -> list[str]:
        return sorted(self._nodes)

    def neighbors(self, skill_id: str, edge_type: str | None = None) -> list[tuple[str, str]]:
        """All outgoing (neighbor, type) pairs, sorted. Optionally filtered to a
        single edge type."""
        items = sorted(self._adj.get(skill_id, set()))
        if edge_type is not None:
            items = [pair for pair in items if pair[1] == edge_type]
        return items

    def walkable_neighbors(self, skill_id: str) -> list[tuple[str, str]]:
        """Navigable neighbors only — excludes ``conflicts_with``."""
        return [
            (n, t) for (n, t) in self.neighbors(skill_id)
            if t in GRAPH_WALKABLE_EDGE_TYPES
        ]

    def conflicts(self, skill_id: str) -> list[str]:
        """Skill ids this skill declares (or is declared in) conflict with."""
        return sorted({n for (n, t) in self.neighbors(skill_id) if t == "conflicts_with"})

    def bounded_expand(self, seeds: list[str], max_nodes: int) -> list[dict[str, str]]:
        """Breadth-first expansion from ``seeds`` over walkable edges.

        Returns up to ``max_nodes`` entries, each ``{"id", "via", "edge"}`` where
        ``via``/``edge`` record the navigable edge that pulled the skill in
        (empty for the seeds themselves). Seeds are visited first, in the order
        given; neighbours are visited in sorted order. The walk is bounded by
        ``max_nodes`` so a dense graph can never produce an unbounded path.
        """
        ordered: list[dict[str, str]] = []
        seen: set[str] = set()
        queue: deque[tuple[str, str, str]] = deque()

        for sid in seeds:
            if sid not in seen:
                seen.add(sid)
                ordered.append({"id": sid, "via": "", "edge": ""})
                queue.append((sid, "", ""))

        while queue and len(ordered) < max_nodes:
            current, _via, _edge = queue.popleft()
            for neighbor, etype in self.walkable_neighbors(current):
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                ordered.append({"id": neighbor, "via": current, "edge": etype})
                queue.append((neighbor, current, etype))
                if len(ordered) >= max_nodes:
                    break
        return ordered[:max_nodes]

    def collect_conflicts(self, skill_ids: Iterable[str]) -> list[dict[str, str]]:
        """All conflict pairs within ``skill_ids`` as advisory signals."""
        selected = set(skill_ids)
        pairs: list[tuple[str, str]] = []
        for sid in sorted(selected):
            for other in self.conflicts(sid):
                if other in selected:
                    a, b = sorted((sid, other))
                    if (a, b) not in pairs:
                        pairs.append((a, b))
        return [{"source": a, "target": b, "type": "conflicts_with"} for a, b in pairs]
