# NexSkill

NexSkill is a local development accelerator for agent-assisted software work.
It selects the right skill path for a task, runs deterministic proof checks, and
writes evidence-backed reports so project owners can decide what happens next.

```text
NexSkill guides the work.
NexSkill selects the right skill path.
NexSkill proves the result.
```

NexSkill is deliberately bounded: it advises, plans, checks, and reports. It
does not automatically approve, merge, release, or replace a project owner's
gates.

## Why NexSkill

Agent-assisted development gets faster when the agent starts with the right
workflow and safer when local evidence checks the result. NexSkill turns that
loop into one product:

| Capability | What it gives you |
|---|---|
| Skill-guided work | Reusable skill packages for planning, building, testing, reviewing, and closeout. |
| Deterministic planning | A bounded, repeatable skill path for the task at hand. |
| Graph-aware selection | Skill dependencies, conflicts, and relationships are visible instead of guessed. |
| Local proof | Project checks, evidence JSONL, and pass/warn/fail outcomes. |
| Owner-ready reports | JSON and Markdown reports that summarize what passed, what failed, and what remains. |
| Lane safety | A preflight command that catches wrong-branch or wrong-worktree starts before work collides. |
| Portable packaging | The wheel ships the built-in skills and scaffold templates, so NexSkill works outside the source checkout. |

## Install

NexSkill is a pure-Python package with no runtime dependencies. It supports
Python 3.10 and newer.

```bash
python -m pip install .
```

To build and install the release wheel from a checkout:

```bash
python -m pip install build
python -m build --wheel
python -m pip install dist/nexskill-*.whl
```

The installed command is:

```bash
nexskill --help
```

## Quickstart

Run NexSkill from inside any repository:

```bash
nexskill init
nexskill plan "add a small repo change"
nexskill check --repo .
nexskill closeout --repo .
```

`nexskill init` creates a `.nexskill/` directory, seeds the built-in starter
skills, and writes a portable config. Planning, checks, and closeout all support
human output and a stable JSON envelope.

```bash
nexskill plan "prepare a release" --repo . --json
```

```json
{
  "ok": true,
  "schema_version": "nexskill.v1",
  "op": "plan",
  "result": {}
}
```

## Add Skills

Future skills do not require core-code changes. Scaffold a new skill package,
edit the generated files, validate, and plan again:

```bash
nexskill skill scaffold reviewing.checklist --repo . \
  --name "Review Checklist" \
  --summary "Runs a fixed review checklist over a change." \
  --stage verifying

nexskill skill validate --repo .
nexskill plan "review a change" --repo .
```

Skill packages use the `nexskill.skill.v1` manifest contract and a local
entrypoint such as `SKILL.md`. See:

- [Skill development guide](docs/sdk/developing-skills.md)
- [Manifest schema reference](docs/sdk/manifest-schema.md)
- [Example skill packages](examples/skills/)

## Command Family

```text
nexskill init [--repo <path>] [--force]
nexskill plan "<task>" [--repo <path>] [--json]
nexskill check [--repo <path>] [--json]
nexskill closeout [--repo <path>] [--json]
nexskill skill list [--repo <path>] [--json]
nexskill skill validate [--repo <path>] [--json]
nexskill skill scaffold <id> [--name <name>] [--summary <text>]
                          [--stage <stage>] [--force] [--repo <path>] [--json]
nexskill preflight [--repo <path>] [--expected-branch <name>]
                   [--expected-base <ref>] [--allow-untracked <glob>] [--json]
```

## What NexSkill Writes

```text
.nexskill/config.json           project config
.nexskill/skills/               local skill packages
.nexskill/graph.json            optional skill relationship overlay
.nexskill/evidence.jsonl        append-only local evidence
.nexskill/reports/latest.json   machine-readable closeout
.nexskill/reports/latest.md     owner-readable closeout
```

## Release Status

NexSkill v1.0 is the first complete product foundation:

- one public command family;
- one extensible skill manifest contract;
- one deterministic planner;
- one local proof layer;
- one report layer;
- one lane preflight;
- one self-contained installable package.

The release is intended for local development acceleration and project-level
evidence. Package-index publication, host integrations, auto-merge authority,
and release automation are separate owner decisions.

## Documentation

- [NEXSKILL.md](NEXSKILL.md) - product entry point for agents and maintainers.
- [Documentation index](docs/INDEX.md) - complete repository documentation.
- [v1.0 release notes](docs/releases/v1.0.0.md) - release summary and checks.
- [Agent guidance](AGENTS.md) - operating rules for work in this repository.

## Provenance

This repository includes legacy graph-research and benchmark material for
provenance and reproducibility. It is kept separate from the NexSkill product
path. Start with the NexSkill command family above unless you are intentionally
working on the archived research workflow.

## License

MIT - see [LICENSE](LICENSE).
