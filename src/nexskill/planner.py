"""NexSkill graph planner.

Produces a bounded, deterministic skill path for a task using manifest metadata
only — stages, tags, inputs/outputs, and declared ``depends_on`` /
``conflicts_with`` relationships. No embeddings, no network, no API keys: the
planner is reproducible for the same registry and task input.

Selection model:

1. Score every skill against the task by lexical overlap of the task tokens with
   the skill's name, summary, tags, inputs, and outputs.
2. Seed the path with skills whose score is above a small threshold, capped to a
   bounded number of seeds.
3. Expand transitive ``depends_on`` so prerequisites are included.
4. Order steps by the canonical stage pipeline, then by skill id (deterministic).
5. Surface any ``conflicts_with`` pairs inside the selected set as advisory
   signals — never silently chosen.

The planner advises; it never claims the selected skills prove work readiness.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .contracts import PlanResult, PlanStep
from .registry import LoadedSkill, SkillRegistry

#: Canonical ordering of stages in a development workflow. Skills whose stage is
#: not listed here are appended after known stages, sorted by id.
STAGE_PIPELINE = ("planning", "building", "verifying", "closing")

#: Max seed skills selected by lexical score before dependency expansion.
MAX_SEEDS = 6
#: Max total steps in a plan (the path must stay bounded).
MAX_STEPS = 12
#: Token-score floor for a skill to be considered a seed.
SEED_SCORE_FLOOR = 1

_TOKEN_RE = re.compile(r"[a-z0-9]+")


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
    """Bounded, deterministic metadata planner."""

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    def plan(self, task: str) -> PlanResult:
        task = (task or "").strip()
        if not task:
            from .contracts import NexSkillError
            raise NexSkillError("PLAN_NO_TASK", "A task description is required for planning.")

        task_tokens = _tokens(task) - _STOPWORDS

        # 1. Score and seed.
        scored: list[_ScoredSeed] = []
        for skill in self._registry.all():
            score = _score_skill(task_tokens, skill)
            if score >= SEED_SCORE_FLOOR:
                scored.append(_ScoredSeed(skill, score))
        if not scored:
            # No lexical match: fall back to a bounded planning-stage default so
            # the user still gets a useful path rather than an empty plan.
            scored = [
                _ScoredSeed(skill, 0)
                for skill in self._registry.by_stage("planning")[:MAX_SEEDS]
            ]
            if not scored and self._registry.all():
                # Last resort: the alphabetically-first skills, bounded.
                scored = [_ScoredSeed(skill, 0) for skill in self._registry.all()[:MAX_SEEDS]]

        # Sort seeds by descending score, then id for determinism, then cap.
        scored.sort(key=lambda s: (-s.score, s.skill.id))
        seeds = [s.skill for s in scored[:MAX_SEEDS]]

        # 2. Expand transitive dependencies.
        selected_ids: list[str] = []
        selected_set: set[str] = set()
        self._expand_deps(seeds, selected_ids, selected_set)

        # 3. Resolve loaded skills and order by stage then id.
        selected = [self._registry.require(sid) for sid in selected_ids]
        selected.sort(key=lambda s: (min(_stage_rank(st)[0] for st in s.manifest.stages), s.id))

        # 4. Bound the path.
        selected = selected[:MAX_STEPS]

        # 5. Surface conflicts inside the selected set (advisory).
        conflicts = self._collect_conflicts(selected_set)
        warnings = self._collect_warnings(task, selected, scored, conflicts)

        steps = [
            PlanStep(
                skill_id=s.id,
                name=s.manifest.name,
                summary=s.manifest.summary,
                stage=s.manifest.stages[0],
                reason=self._reason_for(s, scored),
            )
            for s in selected
        ]
        stages_seen: list[str] = []
        for st in STAGE_PIPELINE:
            if any(st in s.manifest.stages for s in selected):
                stages_seen.append(st)

        return PlanResult(
            task=task,
            stages=stages_seen,
            steps=steps,
            conflicts=conflicts,
            warnings=warnings,
        )

    # ------------------------------------------------------------------

    def _expand_deps(
        self,
        seeds: list[LoadedSkill],
        ordered: list[str],
        seen: set[str],
    ) -> None:
        """Add seeds and their transitive ``depends_on`` in dependency-first
        order using DFS, de-duplicated."""
        stack = list(seeds)
        # Process in reverse so earlier seeds land first when deps tie.
        for skill in reversed(stack):
            self._dfs(skill.id, ordered, seen, [])

    def _dfs(self, skill_id: str, ordered: list[str], seen: set[str], path: list[str]) -> None:
        if skill_id in seen:
            return
        if skill_id in path:
            # Dependency cycle declared in manifests — record nothing, avoid
            # infinite recursion. The planner stays total.
            return
        skill = self._registry.get(skill_id)
        if skill is None:
            return
        # Dependencies first (prerequisites before dependents).
        for dep in skill.manifest.depends_on:
            self._dfs(dep, ordered, seen, path + [skill_id])
        if skill_id in seen:
            return
        seen.add(skill_id)
        ordered.append(skill_id)

    def _collect_conflicts(self, selected_set: set[str]) -> list[dict[str, str]]:
        pairs: list[tuple[str, str]] = []
        for sid in sorted(selected_set):
            skill = self._registry.get(sid)
            if skill is None:
                continue
            for other in skill.manifest.conflicts_with:
                if other in selected_set:
                    a, b = sorted((sid, other))
                    if (a, b) not in pairs:
                        pairs.append((a, b))
        return [{"source": a, "target": b, "type": "conflicts_with"} for a, b in pairs]

    def _collect_warnings(
        self,
        task: str,
        selected: list[LoadedSkill],
        scored: list[_ScoredSeed],
        conflicts: list[dict[str, str]],
    ) -> list[str]:
        warnings: list[str] = []
        if not selected:
            warnings.append("No skills matched the task; the registry may be empty.")
        if any(s.score == 0 for s in scored) and scored:
            warnings.append(
                "Task had no strong keyword match; a default skill path was returned. "
                "Refine the task description for a tighter selection."
            )
        for c in conflicts:
            warnings.append(
                f"Skills {c['source']} and {c['target']} declare a conflict; review before using both."
            )
        return warnings

    def _reason_for(self, skill: LoadedSkill, scored: list[_ScoredSeed]) -> str:
        match = next((s for s in scored if s.skill.id == skill.id), None)
        if match and match.score > 0:
            return f"Matched the task by {match.score} keyword(s)."
        if any(skill.id == d for s in self._registry.all() for d in s.manifest.depends_on):
            return "Included as a declared dependency of another selected skill."
        return "Selected as a default planning-stage skill."
