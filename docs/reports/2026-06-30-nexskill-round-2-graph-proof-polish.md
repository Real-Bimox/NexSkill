# NexSkill round 2 graph + proof + polish - round report

**Status:** Round complete; ready for review
**Date:** 2026-06-30
**Owner:** Bahram Boutorabi
**Branch:** `nexskill/round-2-graph-proof-polish` (based on
`nexskill/round-1-foundation`)

## What landed

This round deepens the round-1 foundation along four axes — graph-aware
planning, a portable proof baseline, performance evidence, and report
snapshots — plus a second-repo dogfood path, all additive and behavior-
preserving.

- **Graph-connected planner.** A new NexSkill-native, dependency-free typed-edge
  graph (`src/nexskill/graph.py`) drives planning. It is built from manifest
  edges (`depends_on`, `conflicts_with`) and an optional, NexSkill-owned overlay
  `.nexskill/graph.json` (`nexskill.graph.v1`) that adds the richer relations
  (`composes_with`, `specializes`, `similar_to`). The planner now seeds by
  relevance, guarantees the `depends_on` prerequisite closure, then expands over
  the other navigable edges within the bounded step budget. `conflicts_with` is
  never traversed; declared conflicts in the selected set surface as advisory
  signals. With no overlay file the walkable edges reduce to manifest
  `depends_on`, so a manifest-only project plans exactly as in round 1. An
  invalid overlay fails closed (`GRAPH_INVALID`).
- **Portable default check set.** `nexskill init` now enables three advisory,
  dependency-light built-in checks (`skills-valid`, `report-hygiene`,
  `git-clean`) via a new `default_checks` config field. Each is `required:
  false`: the worst outcome is a warning, never a blocker, and a check whose
  precondition is absent reports `skipped` (e.g. `git-clean` outside a git
  repository). A fresh project therefore gets a meaningful `check` out of the
  box without hand-editing config and without any external tool dependency.
- **Latency / performance evidence.** `plan`, `check`, and `closeout` now
  measure wall-clock latency. Plan and closeout record `duration_ms` into
  evidence; all three surface a `performance` section in the report (JSON and a
  Markdown "Performance" block). On a warm cache these run in well under the
  2-second target.
- **Markdown report snapshots.** Golden-file coverage
  (`tests/snapshots/report_passed.md`, `report_failed.md`) pins the exact
  owner-facing Markdown for representative report states, regenerable with
  `NEXSKILL_UPDATE_SNAPSHOTS=1`.
- **Second-repo dogfood + manifest-only extension.** An integration test stands
  up a second, independent fixture repository, drops in a project-specific skill
  (`deploying.release-prep`) by manifest alone, and runs validate → list → plan
  → closeout — proving both portability and the no-core-code-change extension
  rule in one path.

## What was verified

- Full test suite passes: **150 tests** (was 121 in round 1; +29 new), no
  regressions to the round-1 foundation or the existing graph package.
- New coverage: NexSkill graph (graph edge validation, overlay fail-closed,
  manifest-edge construction, walkable traversal excluding conflicts, bounded
  determinism, conflict collection), planner overlay expansion (related skill
  pulled only when an overlay edge exists; deterministic), default built-in
  checks (advisory/skip/never-block, broken-manifest warning, unknown-id skip),
  latency evidence, report snapshots, second-repo dogfood, overlay edge count.
- Round-1 command flow still works end to end: `init -> plan -> check ->
  closeout` on a fresh fixture produces config, a bounded multi-stage path,
  append-only evidence, and both report forms.
- Determinism preserved: repeated `plan` runs (with and without an overlay)
  produce identical results.
- Naming scan: `src/nexskill`, `NEXSKILL.md`, seed skills, new tests, and
  snapshots contain no forbidden source/provider/model names (the only matches
  are the denylist guardrail constant in `report.py`).
- Attribution scan: no AI/model/tool attribution trailers in new source.
- Default checks pass/skip (never warn or block) on a fresh, non-git fixture, so
  `check` stays green out of the box.

## What changed (files)

```text
src/nexskill/graph.py             new — NexSkill-native typed-edge graph + overlay loader
src/nexskill/planner.py           graph-driven seed + prerequisite closure + bounded expansion
src/nexskill/proof.py             portable built-in checks + run_checks wiring + latency evidence
src/nexskill/contracts.py         + GRAPH_SCHEMA_VERSION, graph edge vocab, default_checks, DEFAULT_BUILTIN_CHECKS
src/nexskill/report.py            + Markdown Performance section
src/nexskill/cli.py               build overlay graph for plan; measure latency for plan/check/closeout
tests/test_nexskill_graph.py      new — graph unit tests
tests/test_report_snapshot.py     new — Markdown golden-file snapshots
tests/snapshots/*.md              new — report goldens
tests/test_planner.py             + overlay-expansion tests
tests/test_proof.py               + default-check + latency-evidence tests
tests/nexskill_integration/...    + second-repo dogfood + graph-overlay plan tests
docs/reports/2026-06-30-...md      this round report
docs/INDEX.md                      + round-2 report entry
NEXSKILL.md                        + optional graph overlay and default-check notes
```

The existing `src/skilldag/` package, its tests, README, and benchmark/repro
scripts remain unchanged. Round-1 behavior is preserved.

## What remains (next slice)

1. **Overlay authoring + online edges.** Round 2 reads `.nexskill/graph.json`;
   a future slice can let NexSkill propose/record typed edges as a project
   learns them, with the deterministic metadata planner staying the fast path.
2. **Performance budget gate.** Record latency is in evidence; a later slice can
   add an optional check that fails (warns) when warm-cache `plan` latency
   exceeds a configured budget.
3. **Richer built-in checks.** Add more portable advisory checks (e.g. a
   docs-presence or changelog check) behind the same `default_checks` opt-in.
4. **Report snapshot breadth.** Extend golden coverage to overlay-influenced and
   conflict-bearing plans.
5. **Third-repo dogfood.** Run the full sequence against a genuinely separate
   repository on disk before claiming broad portability.

## Trust posture

NexSkill advises, routes, checks, and reports. It does not auto-merge, release,
tag, satisfy owner gates, or expand authority. The graph overlay and default
checks add signal, not authority: reports state what passed and what is advisory;
the owner or project process decides the next action. No runtime-host
integration is included.
