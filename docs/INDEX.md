# NexSkill documentation index

This index separates current implementation docs from NexSkill vNext direction
documents.

## NexSkill product entry

- [NEXSKILL.md](../NEXSKILL.md) - NexSkill product entry point: commands,
  quickstart, manifest format, and how planning works.

## Current implementation

- [Architecture](architecture.md) - current architecture and repository design.
- [Reproducing](reproducing.md) - fresh-clone setup and benchmark walkthrough.
- [Paper reproduction](paper_reproduction.md) - paper-aligned reproduction notes.

## Skill pack SDK

- [Developing skills](sdk/developing-skills.md) - developer guide for authoring
  skills, the `nexskill skill scaffold` command, validation, and selection.
- [Manifest schema reference](sdk/manifest-schema.md) - the full
  `nexskill.skill.v1` field reference.

## NexSkill vNext direction

- [Decision 0001](decisions/0001-nexskill-vnext-approved-direction.md) -
  accepted direction: NexSkill vNext merges skills, skill graph, and proof.
- [NexSkill integration plan](blueprints/NEXSKILL-INTEGRATION-PLAN.md) -
  single coherent implementation plan for the NexSkill skill, graph, proof, and
  report layers.
- [Single-round multi-agent implementation plan](blueprints/NEXSKILL-SINGLE-ROUND-MULTI-AGENT-IMPLEMENTATION-PLAN.md) -
  external-agent-ready plan for the first coordinated development round.
- [NexSkill vNext blueprint](blueprints/NEXSKILL-VNEXT-BLUEPRINT.md) -
  approved blueprint for the first implementation path.
- [NexSkill vNext proposal](proposals/NEXSKILL-VNEXT-PROPOSAL.md) - proposal
  to evolve NexSkill into the combined skill, graph, proof, and reporting
  capability.
- [Development acceleration review](reviews/2026-06-30-development-acceleration-source-review.md) -
  internal source review that informed the NexSkill integration direction.

## Implementation rounds

- [Round 1 foundation report](reports/2026-06-30-nexskill-round-1-foundation.md) -
  what landed, what was verified, and what remains after the first NexSkill
  development round.
- [Round 2 graph + proof + polish report](reports/2026-06-30-nexskill-round-2-graph-proof-polish.md) -
  graph-connected planner, portable default checks, latency evidence, report
  snapshots, and a second-repo dogfood path.
- [Round 2b skill pack SDK report](reports/2026-06-30-nexskill-round-2b-skill-pack-sdk.md) -
  the skill pack template, scaffold command, examples, fixtures, and tests.
- [Round 2c lane isolation preflight report](reports/2026-06-30-nexskill-round-2c-lane-isolation-preflight.md) -
  deterministic, standard-library-only lane preflight that confirms the correct
  branch/worktree and base before starting work.

## Project guidance

- [Agent guidance](../AGENTS.md) - owner-facing reporting preference and
  project guidance for agents working in this repository.
