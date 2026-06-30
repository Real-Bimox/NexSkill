# Decision 0001 - NexSkill vNext approved direction

**Status:** Accepted
**Date:** 2026-06-30
**Owner:** Bahram Boutorabi

## Context

NexSkill currently contains the SkillDAG implementation: typed skill graph,
dependency-aware retrieval, conflict signals, and online graph editing.

The owner wants NexSkill to become the logical product that combines three
capability sources:

1. `Real-Bimox/agent-skills`
2. `Real-Bimox/NexSkill`
3. AutoDev deterministic components

The desired result is simple: make development faster while keeping outcomes
grounded in evidence.

## Decision

NexSkill vNext is approved as the product direction:

```text
NexSkill = Skills + Skill Graph + Proof
```

- `agent-skills` is the thinking layer.
- Current NexSkill/SkillDAG is the routing layer.
- AutoDev-style deterministic checks are the proof layer.

The user-facing rule is:

```text
Skills guide the work.
SkillDAG chooses the right skills.
Deterministic checks prove the result.
```

This decision also approves bringing AutoDev's `AGENTS.md` discipline into this
repository as a NexSkill-owned adaptation. It does not import AutoDev's merge
authority, owner gates, role manuals, release authority, or factory gate.

## Consequences

- NexSkill is the product home for this merged capability.
- Future specs should implement the direction in small slices.
- AutoDev remains the home of AutoDev-specific governance and trust authority.
- NexHarness may become a runtime host later, but it is not the first source of
  product truth.
- Any future auto-merge, release, protected-branch, owner-gate, or Active
  Routing authority requires a separate owner decision.

## Next Artifact

Use [`../blueprints/NEXSKILL-VNEXT-BLUEPRINT.md`](../blueprints/NEXSKILL-VNEXT-BLUEPRINT.md)
as the working blueprint for implementation planning.
