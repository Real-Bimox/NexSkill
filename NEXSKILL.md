# NexSkill

NexSkill is the development accelerator that selects the right skills, guides
the work, and proves the result with deterministic local checks.

```text
NexSkill guides the work.
NexSkill selects the right skill path.
NexSkill proves the result.
```

NexSkill advises, routes, checks, and reports. It does not automatically
approve, merge, release, or satisfy project owner gates. The owner or project
process decides what happens next.

## Quickstart

From inside a repository:

```bash
nexskill init                          # create .nexskill/config.json + seed skills
nexskill plan "add a small repo change"  # bounded, deterministic skill path
nexskill check --repo .                # run configured local checks
nexskill closeout --repo .             # record closeout evidence + report
```

Every command accepts `--json` and returns one envelope:

```json
{
  "ok": true,
  "schema_version": "nexskill.v1",
  "op": "plan",
  "result": {}
}
```

Errors use the same shape with `ok: false`, a stable `UPPER_SNAKE` error code,
and a plain-language message.

## What NexSkill creates

```text
.nexskill/config.json     project config: skill sources, checks, policies
.nexskill/skills/         local skill packages (seeded on init)
.nexskill/graph.json      optional skill-graph overlay (typed relationships)
.nexskill/evidence.jsonl  append-only local evidence events
.nexskill/reports/latest.json   generated report
.nexskill/reports/latest.md     owner-readable summary
```

## Adding a skill

Future skills require no core-code change in the ordinary case:

1. Create a directory under `.nexskill/skills/<skill-id>/`.
2. Add a `manifest.json` (`nexskill.skill.v1`).
3. Add the skill body at the manifest `entrypoint` (typically `SKILL.md`).
4. Run `nexskill skill validate` to confirm the manifest is valid.
5. Run `nexskill plan "<task>"` to see it selected.

### Minimal manifest

```json
{
  "schema_version": "nexskill.skill.v1",
  "id": "planning.task-breakdown",
  "name": "Task Breakdown",
  "summary": "Breaks a development request into verifiable tasks.",
  "stages": ["planning"],
  "inputs": ["task_request"],
  "outputs": ["implementation_plan"],
  "depends_on": [],
  "conflicts_with": [],
  "tags": ["development", "planning"],
  "entrypoint": "SKILL.md"
}
```

Required fields: `schema_version`, `id`, `name`, `summary`, `stages`,
`entrypoint`. The `id` is lowercase with dots, hyphens, or underscores.

## Commands

```text
nexskill init [--repo <path>] [--force]
nexskill plan "<task>" [--repo <path>] [--json]
nexskill check [--repo <path>] [--json]
nexskill closeout [--repo <path>] [--json]
nexskill skill list [--repo <path>] [--json]
nexskill skill validate [--repo <path>] [--json]
nexskill preflight [--repo <path>] [--expected-branch <name>]
                   [--expected-base <ref>] [--allow-untracked <glob>] [--json]
```

## Lane preflight

Before starting work in a NexSkill lane (branch/worktree), run the preflight to
confirm you are in the right place and not about to collide with another lane:

```bash
nexskill preflight \
  --expected-branch nexskill/round-3-my-lane \
  --expected-base origin/nexskill/round-2-graph-proof-polish
```

It is deterministic, standard-library only, and read-only — it inspects git and
worktree state and never mutates the repository. It reports the current worktree
path, branch, HEAD, upstream (if any), tracked changes, and untracked files, and
it exits non-zero (with a stable failure code) when:

- the current branch is not `--expected-branch` (`BRANCH_MISMATCH`);
- the worktree has tracked changes (`TRACKED_CHANGES`);
- unexpected untracked files exist (`UNEXPECTED_UNTRACKED`);
- `--expected-base` is not an ancestor of HEAD (`MISSING_BASE`).

Untracked paths a lane legitimately carries can be allow-listed (repeatable),
for example `--allow-untracked docs/sdk --allow-untracked templates`. The same
check is runnable standalone with `python -m nexskill.preflight`.

## How planning works

`nexskill plan` selects a bounded, ordered skill path. It seeds by relevance to
the task, then walks the NexSkill skill graph: first the guaranteed `depends_on`
prerequisite closure, then other navigable relationships, within a bounded step
budget. It is deterministic and offline: the same registry, overlay, and task
always produce the same path. Declared conflicts inside the selected set are
surfaced as advisory signals, never silently chosen.

The skill graph is built from manifest relationships (`depends_on`,
`conflicts_with`). A project may add an optional overlay at `.nexskill/graph.json`
(`nexskill.graph.v1`) declaring the richer typed relationships
(`composes_with`, `specializes`, `similar_to`) to enrich selection — no
core-code change required. With no overlay, planning uses manifest edges only.

The selected skills guide the work; they do not prove the work is ready. Run
`nexskill check` for proof.

## Default checks

`nexskill init` enables a portable, dependency-light set of advisory checks
(`skills-valid`, `report-hygiene`, `git-clean`) via the `default_checks` config
field. They never block: the worst outcome is a warning, and a check whose
precondition is absent reports `skipped`. `plan`, `check`, and `closeout` also
record their own latency so warm-cache performance is visible in evidence and
the report.

## Trust vocabulary

| Class | Meaning |
|---|---|
| `claimed` | Agent or user said it. Useful, not proof. |
| `derived` | Computed recommendation (e.g. a selected skill path). Advisory. |
| `trusted-local` | A deterministic local check passed. Bounded to this repo/run. |

Reports never include secrets, raw transcripts, provider names, or source
names.

## See also

- [docs/INDEX.md](docs/INDEX.md) - documentation index.
- [docs/blueprints/NEXSKILL-INTEGRATION-PLAN.md](docs/blueprints/NEXSKILL-INTEGRATION-PLAN.md) -
  the coherent integration plan.
- [AGENTS.md](AGENTS.md) - project guidance for agents.
