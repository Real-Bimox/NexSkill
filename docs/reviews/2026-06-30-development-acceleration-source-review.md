# Development Acceleration Source Review

**Status:** ADVISORY - RECOMMENDATIONS ONLY
**Date:** 2026-06-30
**Scope:** How AutoDev should incorporate `Real-Bimox/agent-skills`, and how AutoDev's deterministic operating pieces can become a reusable project-development kit for AutoDev itself, other repositories, and later NexHarness-backed development workflows.

## Executive Answer

Use the skills as **development discipline**, not as authority.

The simplest useful path is a small **Development Acceleration Kit**:

1. a portable skill-routing layer that tells agents which skill to use at each development stage;
2. a small deterministic script layer that proves repository state, handoff quality, checks run, and closeout readiness;
3. a thin project manifest so any repo can opt in without adopting all of AutoDev.

This should not replace AutoDev's gate, owner rules, review model, or release policy. It should package the repeatable parts that make work faster: better intake, better slicing, fewer context mistakes, earlier tests, clearer reviews, and cleaner closeouts.

## Source Inputs

- `Real-Bimox/agent-skills`, inspected via the Codex skill installer on 2026-06-30. The repo exposes 24 installable skills, all present locally.
- AutoDev's current governance and architecture: `AGENTS.md`, `docs/INDEX.md`, `README.md`, `VENDORING.md`, `docs/decisions/0021-right-home-feature-placement.md`, `docs/decisions/0023-logic-placement-and-role-audit.md`, and `docs/ARCHITECTURE.md`.
- Current local safety posture: the main checkout had other uncommitted work, so this review was prepared in an isolated branch/worktree.

This review is not a numbered proposal or spec. It records a recommended direction that should become a proposal/spec only if the owner wants to build it.

## How Might We

How might we make every development project faster and less error-prone by giving agents the right thinking discipline at the right time, while keeping trusted outcomes grounded in deterministic project checks?

## Recommended Direction

Build a **light kit first**, not a full platform.

The kit should be importable into a repo in one of three modes:

| Mode | Best for | What it gives | Risk |
|---|---|---|---|
| Skills only | Small or early repos | Better prompts, intake, planning, testing, review, and closeout discipline | Agents can still claim success without proof |
| Skills plus scripts | Most projects | Skill discipline plus deterministic readiness and closeout evidence | Small maintenance cost |
| Full AutoDev vendoring | Multi-agent repos that need governance | Branch/worktree lanes, role manuals, review/gate flow, report surfaces | Higher process weight |

The recommended first implementation is **skills plus scripts**. It is the smallest version that creates real speed and real trust.

## Skill Incorporation Map

| Development stage | Skills to use | AutoDev process fit | Practical acceleration |
|---|---|---|---|
| Session start and context | `using-agent-skills`, `context-engineering`, `git-workflow-and-versioning` | Agent boot, repo sync, authority-surface reading | Fewer wrong-start sessions and less stale-context work |
| Intake and scope | `interview-me`, `idea-refine`, `spec-driven-development` | Owner mandate, proposal/discussion shaping | Turns vague requests into buildable work faster |
| Design and boundaries | `api-and-interface-design`, `source-driven-development`, `documentation-and-adrs`, `doubt-driven-development` | Architecture review, right-home placement, proposals/specs | Catches bad interfaces and risky assumptions before build |
| Planning and slicing | `planning-and-task-breakdown`, `incremental-implementation` | Lead slicing, lane assignment, handoff planning | Smaller lanes with fewer collisions |
| Build and repair | `test-driven-development`, `debugging-and-error-recovery`, `code-simplification` | Worker implementation and fix cycles | Earlier proof, cleaner fixes, less speculative editing |
| Frontend work | `frontend-ui-engineering`, `browser-testing-with-devtools` | Mission Control and browser-facing features | Better UI quality and real browser verification |
| Hardening | `security-and-hardening`, `performance-optimization`, `observability-and-instrumentation` | Security, reliability, diagnostics, production readiness | Prevents late-stage quality gaps |
| Review and release | `code-review-and-quality`, `ci-cd-and-automation`, `shipping-and-launch`, `deprecation-and-migration` | Reviewer, Doc-Reviewer, release prep, retirement paths | More complete reviews and safer launches |

The key is to make this a **stage router**, not a giant instruction dump. Agents should load only the skill that matches the current work stage.

## AutoDev Process Enhancements

### 1. Add a skill trigger matrix to role prompts

AutoDev should not copy all 24 skills into every role. Instead, each role should get a short trigger matrix:

| Role | Default skill triggers |
|---|---|
| Lead | context, planning, git workflow, right-home/design doubt checks |
| Worker | incremental implementation, TDD, debugging, source-driven development |
| Reviewer | code review, security/performance/observability as relevant |
| Doc-Reviewer | documentation, spec-driven development, doubt-driven development |
| Architect | API/interface design, source-driven development, right-home assessment |
| Monitor | context health, observability, status/report clarity |
| Solo | the full small-project loop: context -> scope -> plan -> TDD -> review -> closeout |

This improves discipline without expanding authority.

### 2. Add a portable "skill router" artifact

Create a small repo artifact such as:

```text
tools/dev-kit/SKILL-ROUTER.md
```

It should answer:

- What kind of task is this?
- Which skill must be loaded?
- What output must exist before moving on?
- What deterministic check proves the output is ready?

This is the bridge between agent judgment and project evidence.

### 3. Add deterministic closeout checks for ordinary projects

AutoDev's strongest idea is not any one script. It is the split between:

- what agents claim; and
- what the repo can independently prove.

A portable kit should include a small script set:

| Script | Purpose | Trust level |
|---|---|---|
| `project-readiness.py` | Checks whether the target repo has rules, test commands, branch status, and expected docs | Trusted local readiness |
| `lane-overlap.py` | Detects file overlap between active lanes or branches | Trusted collision risk |
| `handoff-check.py` | Validates that a task has scope, changed files, verification, and remaining risks | Trusted handoff shape |
| `closeout-check.py` | Runs configured project checks and writes a short closeout report | Trusted closeout evidence |
| `attribution-check.py` | Blocks unwanted tool/model attribution where the project requires it | Trusted policy check |

For non-AutoDev projects, this should be configurable by a small `dev-kit.json` file rather than AutoDev-specific docs.

### 4. Keep AutoDev-specific authority inside AutoDev

Do not move these into a generic skill pack:

- owner approval rules;
- AutoDev's Lead-only main integration authority;
- factory-gate trust decisions;
- release/tag authority;
- Active Routing arming;
- Mission Control live controls;
- AutoDev's own `AGENTS.md`.

Other projects can inherit the pattern, but they need their own governance.

## Portable Kit Shape

Recommended package name:

```text
autodev-development-kit
```

Recommended contents:

```text
autodev-development-kit/
  skills/
    development-acceleration/
      SKILL.md
      templates/
        skill-router.md
        handoff.md
        review.md
        closeout.md
  scripts/
    project-readiness.py
    lane-overlap.py
    handoff-check.py
    closeout-check.py
    attribution-check.py
  templates/
    AGENTS-lite.md
    START-HERE.md
    dev-kit.json
  README.md
```

The kit should install into a target repo under `tools/autodev-kit/` by default. That avoids collisions and mirrors AutoDev's safer Mode-A vendoring posture.

## NexHarness Fit

NexHarness should be considered the future **runtime host**, not the source of AutoDev authority.

Good NexHarness responsibilities:

- launch and supervise development sessions;
- create worktrees;
- route agents to the right skills;
- capture tool/session traces;
- feed structured facts into the repo;
- run the portable closeout checks;
- learn which skill/check combinations lead to better outcomes.

Responsibilities that should stay outside NexHarness unless separately approved:

- deciding that AutoDev may merge;
- satisfying owner gates;
- arming active routing;
- changing release authority;
- treating learned recommendations as trusted facts.

For AutoDev's own development, the kit can be dogfooded on non-trust-boundary tasks. The existing AutoDev gate remains the source of truth.

## Options Considered

### Option A - Prompt-only skill adoption

Fastest to start, but weakest. It improves agent behavior, but it does not prove anything. Useful as a temporary step, not enough as the final solution.

### Option B - Light skills-plus-scripts kit

Recommended. It keeps adoption small while preserving AutoDev's main lesson: agent discipline is useful, but deterministic checks decide whether work is ready.

### Option C - Full AutoDev vendoring everywhere

Strong for serious multi-agent projects, but too heavy as the default for any repo. Keep this for projects that truly need lanes, review roles, and governance.

### Option D - NexHarness-first platform integration

Potentially powerful later, but too much platform tax before the small kit proves value. Start by making NexHarness consume the kit rather than replacing it.

## MVP Scope

The first useful slice should be small:

- one `development-acceleration` skill that routes the 24 skills by task stage;
- one `dev-kit.json` manifest listing test commands, review rules, and closeout requirements;
- three scripts: `project-readiness.py`, `handoff-check.py`, and `closeout-check.py`;
- one AutoDev dogfood report showing it works on a real AutoDev doc-only or low-risk development task;
- one non-AutoDev trial, ideally in NexHarness, to prove portability.

## Not Doing Yet

- Not replacing AutoDev's factory gate.
- Not making skills an authority source.
- Not adding a new runtime dependency to AutoDev.
- Not making every project adopt AutoDev's full role model.
- Not using NexHarness to auto-merge or approve AutoDev work.
- Not building a UI before the command-line kit proves value.

## Assumptions To Validate

| Assumption | How to test |
|---|---|
| Agents will use the right skill more reliably if a router artifact exists | Run two comparable tasks with and without the router and compare rework |
| A small script set gives most of AutoDev's trust benefit | Trial the three-script MVP in NexHarness and one simple repo |
| Full AutoDev vendoring is too heavy for most repos | Time a fresh install and first task closeout in a small repo |
| NexHarness can host the kit cleanly | Build a NexHarness adapter that runs the kit without changing AutoDev authority |

## Recommended Next Step

Approve a proposal for **Development Acceleration Kit v0** with this boundary:

- portable skill router plus deterministic closeout scripts;
- installed under `tools/autodev-kit/`;
- no merge, release, owner-gate, active-routing, or NexHarness authority;
- first validation in AutoDev and NexHarness.

That is the shortest path to better development speed without weakening the trust model.
