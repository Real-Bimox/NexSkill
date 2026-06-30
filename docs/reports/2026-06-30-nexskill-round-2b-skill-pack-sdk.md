# NexSkill round 2b - skill pack SDK

Date: 2026-06-30
Round: 2b
Branch: `nexskill/round-2b-skill-pack-sdk-redo`
Base: `origin/nexskill/round-1-foundation` (`0f25140`)

## Feature / function

Added the skill pack SDK: an authoring surface that lets a developer create a
valid, loadable NexSkill skill package with no core-code change.

- **Skill pack template** (`templates/skill_pack/`) - the `${TOKEN}` source
  template the scaffold renders: `manifest.json`, `SKILL.md`, and a README.
- **`nexskill skill scaffold` command** - renders the template into a concrete
  `.nexskill/skills/<id>/` package, validating the result through the canonical
  `nexskill.skill.v1` contract before writing.
- **Developer guide** (`docs/sdk/developing-skills.md`) and **manifest schema
  reference** (`docs/sdk/manifest-schema.md`) - the authoring docs.
- **Three working example packages** (`examples/skills/`) - demonstrate a
  `depends_on` chain and a `conflicts_with` pair.
- **Validation fixtures** (`tests/fixtures/skill_packs/`) - static valid and
  intentionally-invalid packages with documented expected skip codes.

## What was verified

- New focused suite `tests/test_scaffold.py` (26 tests) covers option
  resolution, rendering, the `scaffold_skill` function, the CLI subprocess path
  (JSON + human + error codes), and fixture-driven registry validation
  (`SKILL_INVALID`, `MANIFEST_MISSING`, `DUPLICATE_ID`).
- Full suite: `python -m unittest discover -s tests` -> 147 tests, OK.
- A scaffolded package loads in the registry and appears in `skill list`;
  `skill validate` passes; re-scaffold without `--force` errors with
  `SCAFFOLD_EXISTS`; `--force` overwrites.

## Global progress

Round 2b is additive to the round 1 foundation. It introduces the authoring
surface promised by the integration plan: skills are now first-class packages
that a developer can scaffold, validate, and have selected by the planner. The
graph/proof/polish lane (round 2, `41818d9`) was not touched.

## Lifecycle status

Implementation complete and verified locally on an isolated worktree. Not
merged, not tagged, not released. Awaiting owner review.

## Owner task

Review the branch `nexskill/round-2b-skill-pack-sdk-redo`. Merge, release, or
tag only on explicit owner approval.

## Owner meaning

Developers can now add NexSkill skills without editing core code. The
scaffolded packages are valid by construction and integrate with the existing
planner and registry. No behavior of existing commands changed.

## Risks

- The scaffold writes into `.nexskill/skills/`; `--force` overwrites an existing
  package directory. Non-`--force` runs are protected by `SCAFFOLD_EXISTS`.
- `examples/` and `tests/fixtures/` are not under a configured skill source, so
  a normal `nexskill init` project never loads them; they are consumed only by
  tests and documentation.
- The example packages declare relationships to each other (e.g.
  `closing.release-notes` depends on `reviewing.self-review`); copying a subset
  into a project leaves dangling references the planner surfaces as warnings,
  not errors.
