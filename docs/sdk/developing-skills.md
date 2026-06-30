# Developing skills - the NexSkill skill pack SDK

Status: Current
Date: 2026-06-30
Owner: Bahram Boutorabi

This guide is the developer entry point for authoring NexSkill skills. It covers
the skill package format, the scaffold command, the manifest schema (see the
companion reference), validation, and how a new skill is selected by the planner.

NexSkill skills guide the work; they are not authority. Adding a skill does not
approve, merge, or release anything. The owner or project process decides what
happens next.

## What a skill package is

A skill package is a directory containing two files:

```text
<skill-id>/
  manifest.json   metadata, declared in the nexskill.skill.v1 schema
  SKILL.md        the skill body, named by the manifest `entrypoint`
```

The directory name is conventional (usually the skill id) but only the manifest
`id` is authoritative. Drop a valid package into a configured skill source and
the registry loads it on the next command - no core-code change.

## The fast path: scaffold

`nexskill skill scaffold` turns the shipped template into a concrete, valid
package in one step:

```bash
nexskill init --repo .
nexskill skill scaffold reviewing.checklist --repo . \
  --name "Review Checklist" \
  --summary "Runs a fixed review checklist over a change." \
  --stage verifying
```

This writes `.nexskill/skills/reviewing.checklist/{manifest.json,SKILL.md}` and
substitutes your values into both files. The generated manifest is validated
through the canonical `nexskill.skill.v1` contract before it is written, so a
scaffolded package is always loadable.

### Scaffold options

| Option | Meaning | Default |
|---|---|---|
| `name` (positional) | Package name; becomes the skill id | required |
| `--id` | Override the skill id | the positional name |
| `--name` | Human-readable skill name | title-cased id |
| `--summary` | One-line summary | a starter sentence |
| `--stage` | Development stage | `building` |
| `--force` | Overwrite an existing package | off |
| `--repo` | Repository root | current directory |
| `--json` | Emit the JSON envelope | off |

The package is written to `<repo>/.nexskill/skills/<id>/`. Re-running scaffold
against an existing id fails with `SCAFFOLD_EXISTS` unless you pass `--force`.

Errors are stable `UPPER_SNAKE` codes: `SCAFFOLD_INVALID_NAME`,
`SCAFFOLD_INVALID_ID`, `SCAFFOLD_EXISTS`, `SCAFFOLD_TEMPLATE_MISSING`.

## The manual path

You can also write a package by hand:

1. Create `.nexskill/skills/<skill-id>/`.
2. Add a `manifest.json` (use the schema reference below or copy an example).
3. Add the body at the manifest `entrypoint` (typically `SKILL.md`).
4. Run `nexskill skill validate` to confirm the manifest is valid.
5. Run `nexskill skill list` to confirm it appears.
6. Run `nexskill plan "<task>"` to see it selected.

Working examples live in [`examples/skills/`](../../examples/skills/). The
template the scaffold uses is in
[`templates/skill_pack/`](../../templates/skill_pack/).

## The SKILL.md body

The body is Markdown with a small YAML frontmatter and a fixed section shape:

```markdown
---
name: <human-readable name>
description: <one-line summary>
---

# <Name>

<Summary sentence.>

## When to use

State the stage and the precondition that must already be true.

## Process

1. First concrete step.
2. Second step, small enough to describe in one sentence.
3. Run the relevant check or test after the work.

## Output

What this skill produces, in a form a deterministic local check can verify.
```

The planner never reads the body. It selects on manifest metadata only - stages,
tags, inputs/outputs, and declared `depends_on` / `conflicts_with`. The body is
for the agent or person doing the work.

## Validation

`nexskill skill validate` loads every configured source and reports any package
that fails to parse. Each skip carries a stable code:

| Code | Meaning |
|---|---|
| `SKILL_INVALID` | Manifest failed schema/field validation. |
| `MANIFEST_MISSING` | A package directory has no `manifest.json`. |
| `DUPLICATE_ID` | A skill id was already loaded from another package. |

A scaffolded package passes validation by construction. When validating a
hand-written package, fix the reported package rather than weakening the
contract.

## How a skill gets selected

`nexskill plan "<task>"` scores every loaded skill by lexical overlap of the
task tokens with the skill's name, summary, tags, inputs, and outputs. It seeds
the path with the top-scoring skills, expands transitive `depends_on`, orders
by the canonical stage pipeline (`planning` -> `building` -> `verifying` ->
`closing`), and surfaces any `conflicts_with` pairs inside the selected set as
advisory signals.

Practical implications for authoring:

- Put the words a task would naturally use into `summary` and `tags`.
- Declare `depends_on` for prerequisites so the planner includes them.
- Declare `conflicts_with` for skills that should not run together; the planner
  surfaces the conflict rather than silently choosing.
- Set `stages` to where in the pipeline the skill belongs.

The selected skills advise; `nexskill check` proves readiness.

## Naming and containment

- Use **NexSkill** as the product name in any skill body, summary, or doc.
- Do not embed source project names, vendor names, model names, or tool brands
  in skill content. Skill bodies are user-facing surfaces.
- Skill ids are lowercase, start with an alphanumeric, and use dots, hyphens, or
  underscores (e.g. `reviewing.checklist`).

## See also

- [Manifest schema reference](manifest-schema.md) - the full `nexskill.skill.v1`
  field reference.
- [Examples](../../examples/skills/) - three working skill packages.
- [Template](../../templates/skill_pack/) - the scaffold source template.
- [NEXSKILL.md](../../NEXSKILL.md) - product entry point and quickstart.
