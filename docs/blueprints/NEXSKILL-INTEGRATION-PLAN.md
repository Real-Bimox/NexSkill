# NexSkill Integration Plan

**Status:** Approved direction - implementation plan
**Date:** 2026-06-30
**Owner:** Bahram Boutorabi

## Purpose

Create one coherent, performant NexSkill solution.

NexSkill must feel like one product, not three parts stitched together. The user
asks for work, NexSkill selects the right skill path, NexSkill guides execution,
NexSkill checks the result, and NexSkill produces evidence that a project owner
can trust locally.

## Product Rule

Use **NexSkill** throughout product and implementation surfaces.

```text
NexSkill guides the work.
NexSkill selects the right skill path.
NexSkill proves the result.
```

Source names, vendor names, model names, and provider names stay out of
user-facing surfaces unless a legal, license, security, or provenance record
requires them.

## Target Architecture

NexSkill has four internal layers behind one product interface:

| Layer | Responsibility | Output |
|---|---|---|
| NexSkill Skill Corpus | Stores reusable development skills and task-stage guidance. | Bounded skill candidates |
| NexSkill Graph Engine | Selects, orders, combines, and rejects skills using typed relationships. | Skill path |
| NexSkill Proof Engine | Runs deterministic local checks against repo state and task evidence. | Pass/fail evidence |
| NexSkill Report Engine | Produces concise human and machine-readable closeout reports. | Report and next action |

The only public product name is NexSkill.

## Core Flow

```text
task request
  -> NexSkill reads project config
  -> NexSkill plans the skill path
  -> NexSkill guides the agent through the selected path
  -> NexSkill checks local evidence
  -> NexSkill writes a closeout report
  -> owner or project process decides the next action
```

## Performance Principles

- Load only the skills needed for the task stage.
- Keep the graph query bounded by task, depth, conflict set, and token budget.
- Cache parsed skill metadata and graph indexes.
- Run proof checks incrementally where possible.
- Produce reports from structured evidence, not from re-reading the whole repo.
- Keep every command deterministic unless explicitly labeled advisory.
- Fail closed when config, graph, or evidence is missing or inconsistent.

## Public Command Shape

First public commands:

```text
nexskill init
nexskill plan "<task>"
nexskill check --repo <path>
nexskill handoff --repo <path>
nexskill closeout --repo <path>
```

All commands should support `--json` with one envelope:

```json
{
  "ok": true,
  "schema_version": "nexskill.v1",
  "op": "plan",
  "result": {}
}
```

Errors use the same shape with `ok: false`, a machine-readable error code, and a
plain-language message.

## Data Contracts

```text
.nexskill/config.json
.nexskill/graph.json
.nexskill/evidence.jsonl
.nexskill/reports/latest.json
.nexskill/reports/latest.md
NEXSKILL.md
tools/nexskill/
```

- `.nexskill/config.json` declares commands, policies, proof checks, and report
  rules.
- `.nexskill/graph.json` stores or points to the active NexSkill graph.
- `.nexskill/evidence.jsonl` records append-only local evidence events.
- `.nexskill/reports/latest.*` are generated from config, graph, and evidence.
- `NEXSKILL.md` is the human/agent entry point for the installed project.
- `tools/nexskill/` is the default repo-local install location.

## Implementation Phases

### Phase 1 - Product Surface and Compatibility

**Goal:** NexSkill has one public name and one forward command shape while
preserving existing behavior.

Acceptance criteria:

- [ ] `nexskill` command exists.
- [ ] Existing graph commands still work through compatibility behavior.
- [ ] README and docs use NexSkill for the product name.
- [ ] No user-facing docs leak source names.
- [ ] Tests cover command compatibility.

Verification:

- [ ] `python -m pytest`
- [ ] `nexskill --help`
- [ ] compatibility command smoke test
- [ ] documentation naming scan

Dependencies: none.

### Phase 2 - NexSkill Skill Corpus

**Goal:** NexSkill can discover and load a curated skill corpus without loading
the whole library into context.

Acceptance criteria:

- [ ] Skill metadata has stable IDs, task stages, summaries, inputs, outputs,
  and conflict hints.
- [ ] Corpus loader validates required fields.
- [ ] Corpus index can be rebuilt deterministically.
- [ ] Invalid skills fail with clear errors.

Verification:

- [ ] corpus fixture tests
- [ ] invalid metadata tests
- [ ] bounded load-size test

Dependencies: Phase 1.

### Phase 3 - NexSkill Graph Engine

**Goal:** NexSkill selects a small, ordered skill path for a task.

Acceptance criteria:

- [ ] Graph supports dependency, composition, specialization, similarity, and
  conflict relationships.
- [ ] `nexskill plan` returns a bounded path with reasons.
- [ ] Conflict detection is visible in human and JSON output.
- [ ] Selection is deterministic for the same config, graph, and task input.

Verification:

- [ ] graph traversal tests
- [ ] conflict fixture tests
- [ ] deterministic repeat-run test
- [ ] output schema test

Dependencies: Phase 2.

### Phase 4 - NexSkill Proof Engine

**Goal:** NexSkill proves local readiness and closeout quality without granting
merge or release authority.

Acceptance criteria:

- [ ] `nexskill check` validates repo config, branch state, command availability,
  policy rules, and required docs.
- [ ] `nexskill handoff` validates scope, changed files, verification, risks,
  and next action.
- [ ] `nexskill closeout` runs configured checks and writes local evidence.
- [ ] Failed checks produce blockers, not automatic repairs.

Verification:

- [ ] clean repo fixture
- [ ] missing config fixture
- [ ] failed command fixture
- [ ] incomplete handoff fixture
- [ ] policy failure fixture

Dependencies: Phase 1.

### Phase 5 - NexSkill Report Engine

**Goal:** NexSkill produces a concise report that a project owner can act on.

Acceptance criteria:

- [ ] Report states task, selected skill path, checks run, pass/fail evidence,
  risks, and next action.
- [ ] Report has Markdown and JSON forms.
- [ ] Report excludes secrets, private prompts, raw transcripts, provider names,
  and source names.
- [ ] Report can be reproduced from config, graph, and evidence.

Verification:

- [ ] report snapshot tests
- [ ] sensitive-field exclusion tests
- [ ] reproducibility test

Dependencies: Phases 3 and 4.

### Phase 6 - Dogfood and Performance Gate

**Goal:** Prove NexSkill works as one coherent solution before expanding scope.

Acceptance criteria:

- [ ] NexSkill runs on this repo using its own config.
- [ ] NexSkill runs on one separate development repo.
- [ ] Planning output is bounded and useful.
- [ ] Proof output is deterministic and reproducible.
- [ ] Command latency is measured and recorded.

Performance targets:

- [ ] `nexskill plan` returns a bounded result in under 2 seconds on a warm cache
  for normal repo tasks.
- [ ] `nexskill check` avoids full-repo scans unless configured.
- [ ] `nexskill closeout` runs only configured checks and records their evidence.

Dependencies: Phases 1-5.

## Parallel Work

Safe to parallelize after Phase 1:

- corpus metadata fixtures;
- graph traversal tests;
- proof-check fixtures;
- report templates;
- documentation naming scan.

Must stay sequential:

- public command envelope;
- config schema;
- evidence schema;
- report schema.

## Risks and Controls

| Risk | Impact | Control |
|---|---|---|
| NexSkill feels like separate tools | Users do not adopt it | One command family, one config, one report format |
| Skill paths get too large | Slow and confusing output | Bound by task stage, graph depth, conflict set, and token budget |
| Proof checks become too project-specific | Low portability | Keep checks configurable and local |
| Reports leak source/provider names | Brand confusion and policy risk | Naming scan and sensitive-field exclusion tests |
| Recommendations are mistaken for authority | Unsafe workflow | Reports say what passed; owner/project process decides next action |

## Definition of Done

NexSkill integration is ready when:

- [ ] all public surfaces use NexSkill as the product name;
- [ ] `nexskill plan` returns a bounded skill path;
- [ ] `nexskill check`, `handoff`, and `closeout` produce deterministic local
  evidence;
- [ ] reports are clear, reproducible, and source-name clean;
- [ ] this repo and one separate repo have successful dogfood reports;
- [ ] runtime or owner-authority expansion remains out of scope unless separately
  approved.
