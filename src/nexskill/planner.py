"""NexSkill graph planner.

Produces a bounded, deterministic skill path for a task. Selection is offline and
reproducible — no embeddings, no network, no API keys — and runs in two stages:

1. **Seed by relevance.** Score every skill against the task by lexical overlap
   of the task tokens with the skill's name, summary, tags, inputs, outputs, and
   stages. The top-scoring skills (bounded by :data:`MAX_SEEDS`) seed the path.
2. **Expand over the graph.** Walk the NexSkill skill graph
   (:class:`nexskill.graph.SkillGraph`) outward from the seeds: first the
   guaranteed ``depends_on`` prerequisite closure, then the other navigable
   relationships (``composes_with`` / ``specializes`` / ``similar_to``) up to the
   :data:`MAX_STEPS` budget. ``conflicts_with`` is never traversed; declared
   conflicts inside the selected set are surfaced as advisory signals instead.

With no overlay graph the walkable edges reduce to manifest ``depends_on``, so a
manifest-only project plans exactly as before. An overlay enriches the same walk
without any core-code change.

The planner advises; it never claims the selected skills prove work readiness.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .contracts import NexSkillError, PlanResult, PlanStep
from .graph import SkillGraph
from .registry import LoadedSkill, SkillRegistry

#: Canonical ordering of stages in a development workflow. Skills whose stage is
#: not listed here are appended after known stages, sorted by id.
STAGE_PIPELINE = ("planning", "building", "verifying", "closing")

#: Max seed skills selected by lexical score before graph expansion.
MAX_SEEDS = 6
#: Max total steps in a plan (the path must stay bounded).
MAX_STEPS = 12
#: Token-score floor for a skill to be considered a seed.
SEED_SCORE_FLOOR = 1

_TOKEN_RE = re.compile(r"[a-z0-9]+")

#: Human-readable phrase for each navigable edge type, used in step reasons.
_EDGE_REASON = {
    "depends_on": "Included as a prerequisite (depends_on).",
    "composes_with": "Related to a selected skill (composes_with).",
    "specializes": "Related to a selected skill (specializes).",
    "similar_to": "Related to a selected skill (similar_to).",
}


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall((text or "").lower()) if len(t) > 2}


_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your",
    "you", "are", "was", "but", "not", "all", "can", "has", "have", "our",
    "use", "using", "add", "make", "get", "set", "new", "one", "two",
}


def _score_skill(task_tokens: set[str], skill: LoadedSkill) -> int:
    """Lexical overlap of task tokens with skill metadata. Pure and
    deterministic."""
    if not task_tokens:
        return 0
    fields = (
        skill.manifest.name,
        skill.manifest.summary,
        " ".join(skill.manifest.tags),
        " ".join(skill.manifest.inputs),
        " ".join(skill.manifest.outputs),
        " ".join(skill.manifest.stages),
        skill.manifest.id,
    )
    field_tokens = _tokens(" ".join(fields)) - _STOPWORDS
    return len(task_tokens & field_tokens)


@dataclass(frozen=True)
class _ScoredSeed:
    skill: LoadedSkill
    score: int


def _stage_rank(stage: str) -> tuple[int, str]:
    """Sort key giving canonical stage order; unknown stages sort last by id."""
    try:
        primary = STAGE_PIPELINE.index(stage)
    except ValueError:
        primary = len(STAGE_PIPELINE)
    return (primary, stage)


class GraphPlanner:
    """Bounded, deterministic graph planner."""

    def __init__(self, registry: SkillRegistry, graph: SkillGraph | None = None) -> None:
        self._registry = registry
        # Default to a manifest-only graph so the planner works without an
        # overlay; callers (the CLI) pass an overlay-enriched graph when present.
        self._graph = graph if graph is not None else SkillGraph.from_registry(registry)

    def plan(self, task: str) -> PlanResult:
        task = (task or "").strip()
        if not task:
            raise NexSkillError("PLAN_NO_TASK", "A task description is required for planning.")

        task_tokens = _tokens(task) - _STOPWORDS

        # 1. Score and seed.
        scored = self._seed(task_tokens)
        scored.sort(key=lambda s: (-s.score, s.skill.id))
        seeds = [s.skill.id for s in scored[:MAX_SEEDS]]

        # 2. Guarantee the depends_on prerequisite closure of the seeds, then
        #    expand over the rest of the navigable graph within budget.
        provenance = self._select(seeds)
        selected_ids = list(provenance.keys())[:MAX_STEPS]

        # 3. Resolve and order by stage then id (deterministic).
        selected = [self._registry.require(sid) for sid in selected_ids]
        selected.sort(key=lambda s: (min(_stage_rank(st)[0] for st in s.manifest.stages), s.id))

        # 4. Surface conflicts inside the selected set (advisory) and warnings.
        conflicts = self._graph.collect_conflicts(selected_ids)
        warnings = self._collect_warnings(selected, scored, conflicts)

        steps = [
            PlanStep(
                skill_id=s.id,
                name=s.manifest.name,
                summary=s.manifest.summary,
                stage=s.manifest.stages[0],
                reason=self._reason_for(s.id, scored, provenance),
            )
            for s in selected
        ]
        stages_seen = [
            st for st in STAGE_PIPELINE if any(st in s.manifest.stages for s in selected)
        ]

        return PlanResult(
            task=task,
            stages=stages_seen,
            steps=steps,
            conflicts=conflicts,
            warnings=warnings,
        )

    # ------------------------------------------------------------------

    def _seed(self, task_tokens: set[str]) -> list[_ScoredSeed]:
        scored: list[_ScoredSeed] = []
        for skill in self._registry.all():
            score = _score_skill(task_tokens, skill)
            if score >= SEED_SCORE_FLOOR:
                scored.append(_ScoredSeed(skill, score))
        if scored:
            return scored
        # No lexical match: fall back to a bounded planning-stage default so the
        # user still gets a useful path rather than an empty plan.
        fallback = [_ScoredSeed(s, 0) for s in self._registry.by_stage("planning")[:MAX_SEEDS]]
        if not fallback and self._registry.all():
            fallback = [_ScoredSeed(s, 0) for s in self._registry.all()[:MAX_SEEDS]]
        return fallback

    def _select(self, seeds: list[str]) -> dict[str, dict[str, str]]:
        """Build the ordered selected set with edge provenance.

        Prerequisites (``depends_on`` closure) are guaranteed first so a plan is
        never missing a declared dependency; the remaining budget is then filled
        by a bounded walk over the other navigable edges.
        """
        provenance: dict[str, dict[str, str]] = {}

        def visit_prereqs(sid: str, stack: tuple[str, ...]) -> None:
            if sid in stack:  # declared dependency cycle — stay total
                return
            for neighbor, etype in self._graph.neighbors(sid, "depends_on"):
                if neighbor not in provenance:
                    visit_prereqs(neighbor, stack + (sid,))
                    provenance.setdefault(neighbor, {"via": sid, "edge": "depends_on"})

        for sid in seeds:
            if sid not in provenance:
                provenance[sid] = {"via": "", "edge": ""}
            visit_prereqs(sid, ())

        # Fill remaining budget with other navigable relationships.
        if len(provenance) < MAX_STEPS:
            for entry in self._graph.bounded_expand(list(provenance.keys()), MAX_STEPS):
                sid = entry["id"]
                if sid not in provenance:
                    provenance[sid] = {"via": entry["via"], "edge": entry["edge"]}
        return provenance

    def _collect_warnings(
        self,
        selected: list[LoadedSkill],
        scored: list[_ScoredSeed],
        conflicts: list[dict[str, str]],
    ) -> list[str]:
        warnings: list[str] = []
        if not selected:
            warnings.append("No skills matched the task; the registry may be empty.")
        if scored and all(s.score == 0 for s in scored):
            warnings.append(
                "Task had no strong keyword match; a default skill path was returned. "
                "Refine the task description for a tighter selection."
            )
        for c in conflicts:
            warnings.append(
                f"Skills {c['source']} and {c['target']} declare a conflict; review before using both."
            )
        return warnings

    def _reason_for(
        self,
        skill_id: str,
        scored: list[_ScoredSeed],
        provenance: dict[str, dict[str, str]],
    ) -> str:
        match = next((s for s in scored if s.skill.id == skill_id), None)
        if match and match.score > 0:
            return f"Matched the task by {match.score} keyword(s)."
        edge = provenance.get(skill_id, {}).get("edge", "")
        if edge in _EDGE_REASON:
            return _EDGE_REASON[edge]
        return "Selected as a default planning-stage skill."
