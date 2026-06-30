# NexSkill - project guidelines for agents

> Standing rules for any AI agent working in this repository.
> Owner: Bahram Boutorabi.
> This file is adapted from AutoDev's operating discipline, but it is
> NexSkill-owned. AutoDev's merge gates, role manuals, owner policy, and
> factory authority do not transfer here unless separately approved.

NexSkill is the product home for the combined development capability:

```text
agent-skills guide the work
SkillDAG selects and relates the skills
AutoDev-style deterministic checks prove the result
```

The approved direction is recorded in
[`docs/decisions/0001-nexskill-vnext-approved-direction.md`](docs/decisions/0001-nexskill-vnext-approved-direction.md)
and the forward blueprint is
[`docs/blueprints/NEXSKILL-VNEXT-BLUEPRINT.md`](docs/blueprints/NEXSKILL-VNEXT-BLUEPRINT.md).

## 0. Orientation - read this first

The git repo, kept in sync with GitHub, is the durable memory. If it matters,
commit and push it. Local chat or machine memory is not enough.

On session start:

1. Sync first: run `git pull` and reconcile before changing files.
2. Read this `AGENTS.md`.
3. Read [`docs/INDEX.md`](docs/INDEX.md).
4. Read [`README.md`](README.md) for current package context.
5. For NexSkill vNext work, also read the approved decision and blueprint linked
   above.

When a durable decision is made, record it in `docs/decisions/` or the relevant
blueprint/spec before relying on it later.

## 1. No third-party attribution in repo artifacts

Do not add AI/model/tool attribution to commits, tags, PR titles or
descriptions, branch names, or file content.

Forbidden examples include co-author trailers naming an AI/model/tool,
machine-generated-by statements, created/authored-by tool statements, and
machine-attribution emojis or similar labels.

Commit messages must end at the last substantive sentence. No trailers,
signatures, or machine-attribution footers.

## 2. What NexSkill is

NexSkill vNext merges three capabilities into one product:

- `Real-Bimox/agent-skills` - reusable development skills and work discipline.
- Current NexSkill/SkillDAG - typed skill graph, dependency-aware retrieval,
  conflict signals, and online graph edits.
- AutoDev-style deterministic components - portable checks that verify project
  readiness, handoff quality, closeout quality, policy hygiene, and evidence.

Standing tenets:

- Skills guide the work; they are not authority.
- SkillDAG selects a bounded skill bundle; it does not prove the work is ready.
- Deterministic checks prove local claims wherever practical.
- NexSkill accelerates and verifies development; it does not automatically
  approve, merge, release, or satisfy owner gates.
- AutoDev-specific authority stays in AutoDev.
- NexHarness may later host NexSkill workflows, but it is not the source of
  NexSkill product truth.

## 3. Stack and dependency policy

Current NexSkill is a Python package with a SkillDAG CLI and inert Markdown
documentation.

- Preserve existing `skilldag` behavior until a compatibility-preserving
  migration introduces `nexskill` commands.
- Keep deterministic proof scripts small, auditable, and dependency-light.
- New runtime dependencies must be justified in a proposal/spec or decision.
- Do not weaken existing benchmark, reproduction, or graph behavior while adding
  NexSkill vNext layers.

## 4. How we work

For product-direction changes:

1. Record the decision or proposal in `docs/decisions/`, `docs/blueprints/`,
   `docs/proposals/`, or `docs/specs/`.
2. Keep implementation slices small and traceable.
3. Update `docs/INDEX.md` when new durable docs are added.
4. Run relevant checks before claiming work is complete.
5. Push completed work to GitHub.

For implementation work, prefer this loop:

```text
scope -> plan -> test/check -> implement -> verify -> document -> commit -> push
```

## 5. Branches and writer safety

- `main` is the integration target and source of truth.
- Use short-lived branches for non-trivial work.
- When multiple agents work concurrently, each agent uses its own branch and
  ideally its own worktree.
- One writer owns a file at a time. Coordinate before editing shared docs such
  as this file, `README.md`, `docs/INDEX.md`, and active blueprints/specs.
- Do not force-push, rewrite history, delete branches, or delete existing files
  without explicit owner approval.

## 6. Halt-to-owner conditions

Stop and ask the owner before:

- handling secrets or credentials;
- making license, legal, or attribution-policy decisions;
- expanding scope beyond the current request;
- making irreversible or destructive changes;
- pushing directly to a protected branch;
- creating a release or tag;
- granting NexSkill any auto-merge, release, protected-branch, owner-gate, or
  AutoDev authority;
- accepting product risk from unresolved high-severity findings.

Owner questions must be short and framed in product/user impact terms.

## 7. Release policy

A NexSkill version is not released until:

- the code and docs are in sync;
- relevant tests or reproduction checks have been run;
- release notes exist;
- the git tag and GitHub Release both exist.

Release/tag actions require explicit owner approval.

## 8. Owner-facing reporting

Keep owner updates concise, plain-language, and decision-focused.

Progress reports should focus on feature/function impact, not file-by-file
activity. When useful, use:

- `Feature / function`
- `Global progress`
- `Lifecycle status`
- `Owner task`
- `Owner meaning`

Routine closeouts should state what changed, what was verified, where it was
pushed, and what remains.
