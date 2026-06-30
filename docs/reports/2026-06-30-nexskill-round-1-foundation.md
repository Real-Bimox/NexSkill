# NexSkill round 1 foundation - round report

**Status:** Round complete; ready for review
**Date:** 2026-06-30
**Owner:** Bahram Boutorabi
**Branch:** `nexskill/round-1-foundation` (based on `codex/nexskill-vnext-docs`)

## What landed

This round delivered the first working NexSkill foundation as one coherent
product, behind one public command family, preserving the existing graph
package and behavior unchanged.

- **One public NexSkill command family**: `nexskill init`, `plan`, `check`,
  `closeout`, plus `nexskill skill list` / `skill validate`. All commands
  support `--json` and emit one envelope
  (`{ok, schema_version, op, result|error}`).
- **One extensible skill package contract**: `nexskill.skill.v1` manifests with
  boundary-first validation. Invalid manifests fail with a stable code and never
  enter the registry. Future skills are added by dropping a valid package into a
  configured source - no core-code change in the ordinary case.
- **One bounded skill-path planner**: deterministic, offline, metadata-only
  selection (stages, tags, inputs/outputs, declared `depends_on` /
  `conflicts_with`). Same registry + task always produce the same path. Declared
  conflicts in the selected set are surfaced as advisory signals.
- **One local proof/check layer**: runs configured checks, treats failed
  required checks as blockers and failed optional checks as warnings, and writes
  append-only `nexskill.evidence.v1` JSONL.
- **One concise report layer**: `latest.json` and `latest.md`, reproducible from
  config and evidence, additive across future sections.
- **Seed skill corpus**: four shipped skill packages (planning, building,
  verifying, closing) copied into `.nexskill/skills` on `init`, so planning
  works out of the box.
- **Product entry point**: `NEXSKILL.md`, indexed from `docs/INDEX.md`.

## What was verified

- Full test suite passes: **121 tests** (34 legacy graph + 87 new NexSkill),
  no regressions to the existing graph package.
- Lane verification: contracts (27), registry (16), planner (7), proof (10),
  report (8), CLI (11), integration (8).
- End-to-end fixture sequence `init -> plan -> check -> closeout` produces
  config, a bounded multi-stage skill path, evidence JSONL, and both report
  forms.
- NexSkill runs `plan` and `check` against a throwaway repo (dogfood).
- Naming scan: generated reports and evidence contain no forbidden source names
  (`skilldag`, `autodev`, `agent-skills`, `graph-of-skills`, `real-bimox`,
  `openai`, `gpt`).
- Policy scan: no AI/model/tool attribution trailers in new source; new
  user-facing surfaces use the NexSkill product name.
- Secret hygiene: command output embedded in evidence is best-effort redacted,
  and the raw command string is not persisted into evidence (evidence-safe view).

## What changed (files)

```text
src/nexskill/                     new package (contracts, registry, planner, proof, report, cli, __main__)
data/nexskill_skills/             seed skill corpus (4 packages)
tests/test_{contracts,registry,planner,proof,report,cli}.py
tests/nexskill_integration/       end-to-end + naming/policy scans
NEXSKILL.md                       product entry point
docs/reports/2026-06-30-...md     this round report
pyproject.toml                    + nexskill console script
.gitignore                        + .nexskill/ runtime state; allow data/nexskill_skills/
docs/INDEX.md                     + NEXSKILL.md entry
```

The existing `src/skilldag/` package, its tests, README, and benchmark/repro
scripts are unchanged. Existing behavior is preserved.

## What remains (next slice)

These are intentionally out of scope for round 1 and are recommended next
slices:

1. **Owner-configured check wiring**: ship a small, portable default check set
   (e.g. a no-op / git-clean check) behind explicit opt-in, so a fresh project
   can demonstrate a non-trivial `check` without hand-editing config.
2. **Graph-engine integration**: connect the planner to the typed-edge
   `SkillGraph` (depends_on / composes_with / conflicts_with / specializes /
   similar_to) so planning can use learned online edges, not only manifest
   declarations. The deterministic metadata planner remains the fast path.
3. **Performance timing report**: record `plan`/`check` latency to evidence so
   the under-2-seconds warm-cache target is continuously verified.
4. **Markdown report polish and report snapshots**: golden-file snapshot tests
   for `latest.md`.
5. **Second-repo dogfood**: run the full sequence against a separate
   development repository and record results before claiming broad portability.

## Trust posture

NexSkill advises, routes, checks, and reports. It does not auto-merge, release,
tag, satisfy owner gates, or expand authority. Reports state what passed; the
owner or project process decides the next action. No runtime-host integration
is included.
