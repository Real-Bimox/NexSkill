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
```

## How planning works

`nexskill plan` selects a bounded, ordered skill path using skill metadata only
(stages, tags, inputs/outputs, and declared `depends_on` / `conflicts_with`
relationships). It is deterministic and offline: the same registry and task
always produce the same path. Declared conflicts inside the selected set are
surfaced as advisory signals, never silently chosen.

The selected skills guide the work; they do not prove the work is ready. Run
`nexskill check` for proof.

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
