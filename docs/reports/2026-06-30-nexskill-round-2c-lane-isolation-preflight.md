# NexSkill round 2c lane isolation preflight - round report

**Status:** Round complete; ready for review
**Date:** 2026-06-30
**Owner:** Bahram Boutorabi
**Branch:** `nexskill/round-2c-lane-isolation-preflight` (based on
`origin/nexskill/round-2-graph-proof-polish`)

## What landed

A small, deterministic, standard-library-only **lane isolation preflight** that
an agent runs before starting NexSkill work to confirm it is in the correct
branch/worktree and is not about to collide with another lane.

- **New module** `src/nexskill/preflight.py` — read-only: it inspects git and
  worktree state, makes no network call, and never mutates the repository.
- **Reports** the current worktree path, branch, HEAD commit, upstream (if any),
  dirty tracked files, untracked files, whether the current branch matches the
  expected branch, and whether the expected base is an ancestor of HEAD.
- **Human and JSON output.** JSON uses the NexSkill envelope
  (`{ok, schema_version, op: "preflight", result}`); the full lane state is
  present in `result` on both pass and fail, with a `failures` list of stable
  codes.
- **Fails clearly** (non-zero exit) on: `BRANCH_MISMATCH`, `TRACKED_CHANGES`,
  `UNEXPECTED_UNTRACKED`, `MISSING_BASE`, and `NOT_A_GIT_REPO`. Untracked paths a
  lane legitimately carries can be allow-listed (`--allow-untracked`, repeatable;
  glob or path-prefix).
- **Two entry points**, both NexSkill-named: the product subcommand
  `nexskill preflight` and the standalone `python -m nexskill.preflight`.
- **Docs**: a "Lane preflight" usage note in `NEXSKILL.md`.

## What was verified

- Full test suite passes: **162 tests** (150 from round 2 + 12 new preflight
  tests), no regressions.
- New coverage (`tests/test_preflight.py`): clean lane passes; core-state and
  envelope shape; `BRANCH_MISMATCH`, `TRACKED_CHANGES`, `UNEXPECTED_UNTRACKED`
  (and allow-list clearing, glob/prefix), `MISSING_BASE`, `NOT_A_GIT_REPO`; CLI
  exit codes; and the integrated `nexskill preflight` subcommand over a real
  temporary git repository.
- The preflight runs against its own lane (dogfood): correct branch, base
  ancestry, clean tree.
- Naming/attribution scan: the new surfaces use only NexSkill naming and carry
  no tool/model attribution.

## Implementation note

A first run surfaced two real bugs that the tests caught: stripping the whole
`git status --porcelain` output discarded the significant leading status column
(shifting file paths by one character), and git collapses untracked directories
by default. Both are fixed — the helper now strips only the trailing newline,
and the status call uses `--untracked-files=all` so nested lane files are listed
and matched individually.

## Scope boundaries honored

- Did not touch `docs/sdk/`, `templates/`, `examples/`, `tests/fixtures/`, the
  round 2b branch, or `main`.
- Work was done in an isolated git worktree on a branch based on
  `origin/nexskill/round-2-graph-proof-polish`.

## What remains (next slice)

1. **Wire preflight into agent lane startup** so each lane runs it automatically
   before editing, with the lane's expected branch/base supplied by the round
   plan.
2. **Optional config-driven allow-list**, so a project can record its expected
   untracked paths once instead of passing flags each run.
3. **Worktree-collision detection across lanes** — report when another lane's
   worktree is checked out on the same branch.

## Trust posture

The preflight advises and reports; it does not mutate the repository, merge,
tag, or grant authority. It states whether a lane is isolated and ready; the
agent or owner decides the next action.
