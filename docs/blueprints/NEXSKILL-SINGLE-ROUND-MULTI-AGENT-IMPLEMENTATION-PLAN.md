# NexSkill Single-Round Multi-Agent Implementation Plan

**Status:** Ready for external-agent development round
**Date:** 2026-06-30
**Owner:** Bahram Boutorabi

## Purpose

This is the handoff plan for one coordinated multi-agent development round.

The goal is to deliver the first working NexSkill foundation:

- one public NexSkill command family;
- one extensible skill package contract;
- one bounded skill-path planner;
- one local proof/check layer;
- one concise report layer;
- tests and docs that make future skill additions simple.

This round must keep NexSkill coherent, expandable, and performant. It must not
turn into a collection of disconnected scripts.

## Product Language Rule

Use **NexSkill** throughout code comments, docs, command help, reports, examples,
tests, and handoffs.

Do not use source project names, vendor names, provider names, model names, or
tool-brand names in user-facing surfaces. Internal provenance belongs only in
dedicated decision records when needed.

## Round Outcome

At the end of this round, a user should be able to run:

```text
nexskill init
nexskill plan "prepare a small repo change"
nexskill check --repo .
nexskill closeout --repo .
```

Expected result:

- NexSkill creates or reads `.nexskill/config.json`.
- NexSkill discovers local skill packages through a stable manifest.
- NexSkill returns a bounded skill path for the task.
- NexSkill runs deterministic local checks.
- NexSkill writes `.nexskill/reports/latest.json` and
  `.nexskill/reports/latest.md`.

## Non-Goals

- No auto-merge.
- No release/tag creation.
- No protected-branch writes.
- No external owner-gate authority.
- No runtime-host integration.
- No broad rewrite of existing graph internals unless required to preserve the
  public NexSkill contracts.
- No loading a full skill library into prompt/context.

## Architecture Contract

All agents must preserve this four-layer architecture:

```text
NexSkill CLI
  -> NexSkill Core Contracts
      -> Skill Registry
      -> Graph Planner
      -> Proof Runner
      -> Report Builder
```

Layer responsibilities:

| Layer | Responsibility | Must not do |
|---|---|---|
| CLI | Parse user intent, call core services, render human/JSON output | Hide errors or mutate repos without explicit command |
| Core Contracts | Define stable dataclasses/schemas and error envelope | Depend on CLI formatting |
| Skill Registry | Discover, validate, index, and cache skill package metadata | Load full skill bodies unless requested |
| Graph Planner | Produce bounded, ordered skill paths with reasons and conflicts | Claim selected skills prove work readiness |
| Proof Runner | Run configured local checks and record evidence | Approve merges or repair failures automatically |
| Report Builder | Summarize plan/check/closeout evidence | Include secrets, raw transcripts, provider names, or source names |

## Public Interface Contract

### Commands

Implement or preserve these commands:

```text
nexskill init [--repo <path>] [--force]
nexskill plan "<task>" [--repo <path>] [--json]
nexskill check [--repo <path>] [--json]
nexskill closeout [--repo <path>] [--json]
```

Optional if low-risk after required commands:

```text
nexskill skill list [--repo <path>] [--json]
nexskill skill validate [--repo <path>] [--json]
```

### JSON Envelope

Every `--json` command returns this shape:

```json
{
  "ok": true,
  "schema_version": "nexskill.v1",
  "op": "plan",
  "result": {}
}
```

Errors use the same envelope:

```json
{
  "ok": false,
  "schema_version": "nexskill.v1",
  "op": "plan",
  "error": {
    "code": "CONFIG_MISSING",
    "message": "Run nexskill init before planning work.",
    "details": {}
  }
}
```

Rules:

- error codes are stable `UPPER_SNAKE`;
- `message` is plain language;
- `details` is optional and must not include secrets;
- future fields are additive;
- breaking schema changes require `schema_version` bump.

## Repo Data Contracts

### `.nexskill/config.json`

Minimum shape:

```json
{
  "schema_version": "nexskill.config.v1",
  "project_name": "example",
  "skill_sources": [
    { "type": "local", "path": ".nexskill/skills" }
  ],
  "checks": [
    { "id": "tests", "command": "configured-test-command", "required": true }
  ],
  "policies": {
    "product_name": "NexSkill",
    "forbid_source_names_in_reports": true
  }
}
```

### Skill Package Manifest

Each skill package has a manifest:

```json
{
  "schema_version": "nexskill.skill.v1",
  "id": "planning.task-breakdown",
  "name": "Task Breakdown",
  "summary": "Breaks a development request into verifiable tasks.",
  "stages": ["planning"],
  "inputs": ["task_request", "repo_context"],
  "outputs": ["implementation_plan"],
  "depends_on": [],
  "conflicts_with": [],
  "tags": ["development", "planning"],
  "entrypoint": "SKILL.md"
}
```

Rules:

- `id` is stable and lowercase with dots or hyphens;
- `schema_version`, `id`, `name`, `summary`, `stages`, and `entrypoint` are
  required;
- unknown optional fields are preserved but ignored unless supported;
- invalid manifests fail validation and do not enter the registry;
- future skills can be added by dropping a package with a valid manifest into a
  configured skill source.

### `.nexskill/evidence.jsonl`

Append-only local evidence event:

```json
{
  "schema_version": "nexskill.evidence.v1",
  "event_id": "local-unique-id",
  "op": "check",
  "status": "passed",
  "timestamp": "2026-06-30T00:00:00Z",
  "summary": "Configured checks passed.",
  "data": {}
}
```

Rules:

- one JSON object per line;
- no raw secrets;
- no raw transcripts;
- no source/provider names in generated reports;
- failed checks are recorded as evidence, not hidden.

## File Ownership for the Round

Each lane owns its files. Do not edit another lane's owned files without
coordinator approval.

| Lane | Owns |
|---|---|
| Lane A - Contracts | `src/nexskill/contracts.py`, `tests/test_contracts.py`, schema docs |
| Lane B - CLI | CLI entrypoint files, command parsing tests |
| Lane C - Skill Registry | registry/index/cache modules and fixtures |
| Lane D - Proof Runner | proof/check modules, check fixtures, evidence writer |
| Lane E - Report Builder | report modules, report templates, snapshot tests |
| Lane F - Integration QA | integration tests, naming scans, final round report |
| Coordinator | `README.md`, `docs/INDEX.md`, this plan, cross-lane conflict resolution |

If the existing package layout makes these exact paths unsuitable, preserve the
lane ownership idea and add compatibility shims instead of exposing legacy names
in new user-facing surfaces.

## Dependency Graph

```text
Lane A - Contracts
  -> Lane B - CLI
  -> Lane C - Skill Registry
  -> Lane D - Proof Runner
  -> Lane E - Report Builder
  -> Lane F - Integration QA
```

Parallelization:

- Lane A must land first.
- Lanes C and D may start from Lane A contracts in parallel.
- Lane B may stub commands after Lane A, then connect to C/D/E as they land.
- Lane E starts once A and D evidence shapes are stable.
- Lane F runs continuously but finalizes last.

## Lane A - Core Contracts

**Description:** Define stable core dataclasses/schemas for commands, skill
manifests, plan results, check results, evidence events, reports, and errors.

Acceptance criteria:

- [ ] JSON envelope helpers exist for success and error responses.
- [ ] Skill manifest validation is contract-first and boundary-validated.
- [ ] Evidence event shape is defined and tested.
- [ ] Contracts do not depend on CLI rendering.

Verification:

- [ ] contract test command;
- [ ] invalid manifest fixture fails with stable error code;
- [ ] success/error envelope snapshots are stable.

Estimated scope: Medium.

## Lane B - NexSkill CLI

**Description:** Add the public NexSkill command family and route commands to
core services.

Acceptance criteria:

- [ ] `nexskill --help` works.
- [ ] `nexskill init` creates `.nexskill/config.json` without overwriting unless
  `--force` is passed.
- [ ] `nexskill plan`, `check`, and `closeout` support `--json`.
- [ ] Human output is concise and uses only NexSkill product language.
- [ ] Existing behavior remains available through compatibility paths.

Verification:

- [ ] CLI unit tests;
- [ ] `nexskill --help`;
- [ ] `nexskill init --repo <fixture>`;
- [ ] JSON envelope tests.

Estimated scope: Medium.

## Lane C - Skill Registry

**Description:** Implement discovery and validation for future skill packages so
new skills can be added simply.

Acceptance criteria:

- [ ] Registry discovers configured local skill sources.
- [ ] Registry validates every manifest.
- [ ] Registry builds a deterministic index.
- [ ] Registry supports list/lookup by ID, stage, tag, and output type.
- [ ] Registry caches parsed metadata without caching full skill bodies into
  command output.
- [ ] Adding a future skill requires only adding a valid package plus manifest.

Verification:

- [ ] registry fixture tests;
- [ ] duplicate ID test;
- [ ] missing field test;
- [ ] invalid entrypoint test;
- [ ] deterministic sort/index test;
- [ ] large corpus bounded-load test.

Estimated scope: Medium.

## Lane D - Proof Runner

**Description:** Implement local proof checks and evidence writing.

Acceptance criteria:

- [ ] `nexskill check` validates config, command availability, branch cleanliness
  where configured, policy rules, and required docs.
- [ ] `nexskill closeout` runs configured checks and records evidence.
- [ ] Required check failure returns non-zero status.
- [ ] Optional check failure is reported but does not fail the whole command.
- [ ] Evidence events are append-only JSONL.

Verification:

- [ ] clean fixture passes;
- [ ] missing config fixture fails;
- [ ] failed required command fixture fails;
- [ ] optional command failure remains warning;
- [ ] evidence JSONL parse test;
- [ ] no secret/source-name leak in generated evidence summary.

Estimated scope: Medium.

## Lane E - Report Builder

**Description:** Produce clear human and JSON reports from plan/check/closeout
evidence.

Acceptance criteria:

- [ ] `latest.json` contains task, plan, checks, status, blockers, warnings, and
  next action.
- [ ] `latest.md` is concise and owner-readable.
- [ ] Reports are reproducible from config and evidence.
- [ ] Reports exclude raw transcripts, secrets, provider names, and source names.
- [ ] Report builder can accept future sections without breaking old reports.

Verification:

- [ ] report snapshot tests;
- [ ] sensitive-field exclusion tests;
- [ ] source-name scan test;
- [ ] reproducibility test.

Estimated scope: Small to Medium.

## Lane F - Integration QA and Round Report

**Description:** Prove the round works end to end and prepare the external-agent
closeout.

Acceptance criteria:

- [ ] Fixture repo can run `init`, `plan`, `check`, and `closeout`.
- [ ] This repo can run at least `plan` and `check`.
- [ ] Test suite passes.
- [ ] Naming scan passes for user-facing surfaces changed in this round.
- [ ] A round report records what landed, what passed, what remains, and the next
  recommended slice.

Verification:

- [ ] configured test command;
- [ ] end-to-end fixture command sequence;
- [ ] docs naming scan;
- [ ] attribution/policy scan;
- [ ] final repository status check.

Estimated scope: Medium.

## Round Coordinator Instructions

1. Start from a clean branch and synced repo.
2. Create one worktree/branch per lane.
3. Assign file ownership exactly as above.
4. Require every lane to read `AGENTS.md` and this plan before editing.
5. Land Lane A first.
6. Let Lanes C and D proceed in parallel after Lane A.
7. Let Lane B wire commands once C/D service APIs stabilize.
8. Let Lane E finish reports after D evidence shape stabilizes.
9. Let Lane F verify continuously and finalize last.
10. Do not merge code that breaks existing behavior or product naming rules.

## External Agent Prompt

Use this prompt for every external agent, replacing bracketed fields:

```text
You are working in the NexSkill repository.

Read AGENTS.md first. Then read:
- docs/blueprints/NEXSKILL-SINGLE-ROUND-MULTI-AGENT-IMPLEMENTATION-PLAN.md
- docs/blueprints/NEXSKILL-INTEGRATION-PLAN.md

You own [LANE NAME].

Rules:
- Use NexSkill as the product name in all user-facing code, docs, help text,
  reports, tests, and examples.
- Do not add source project names, vendor names, provider names, model names, or
  tool-brand names to user-facing surfaces.
- Stay inside your lane's owned files unless the coordinator approves.
- Preserve existing behavior unless your lane explicitly changes it.
- Add tests for every behavior you add.
- Run your lane verification before reporting completion.
- Do not release, tag, auto-merge, force-push, or delete files/branches.

Deliver:
- code/docs for your lane;
- tests;
- verification output summary;
- risks or blockers;
- files changed.
```

## Future Skill Expansion Model

Future skills must be simple to add:

1. Create a skill package directory.
2. Add a valid `nexskill.skill.v1` manifest.
3. Add the skill body at the manifest entrypoint.
4. Run `nexskill skill validate`.
5. Run `nexskill plan` against a fixture task.
6. Commit the package and any graph metadata.

No core-code change should be required for an ordinary new skill. Core-code
changes are allowed only when a new skill needs a genuinely new schema field,
relationship type, proof check type, or report section.

## Design Standards

- Contracts first, implementation second.
- Additive fields over breaking changes.
- Boundary validation for config, manifests, evidence, and command inputs.
- Single JSON envelope for all command output.
- Deterministic sorting for indexes and reports.
- Stable error codes.
- Small modules with clear ownership.
- No full-library prompt loading.
- No hidden repo mutation.
- Generated files must be reproducible.

## Performance Targets

- `nexskill plan` uses cached metadata and bounded graph traversal.
- `nexskill plan` returns a normal task result in under 2 seconds on a warm
  cache.
- `nexskill check` runs only configured checks.
- `nexskill closeout` reuses recorded evidence where safe and records fresh
  command results when configured.
- Large skill sets are indexed once, then queried by metadata and graph edges.

## Final Acceptance for This Round

The round is complete only when:

- [ ] commands exist and use the NexSkill product name;
- [ ] skill packages can be added through manifests;
- [ ] skill planning is bounded and deterministic;
- [ ] local checks produce evidence;
- [ ] closeout reports exist in Markdown and JSON;
- [ ] future skills can be added without core-code edits in the ordinary case;
- [ ] tests pass;
- [ ] naming and policy scans pass;
- [ ] final report identifies remaining work.

## If Scope Must Be Cut

Cut in this order:

1. optional `nexskill skill list` command;
2. advanced graph relationship editing;
3. performance timing report;
4. Markdown report polish.

Do not cut:

- JSON envelope;
- skill manifest validation;
- basic `init`, `plan`, `check`, `closeout`;
- evidence JSONL;
- naming/source-containment checks;
- tests for required behavior.
