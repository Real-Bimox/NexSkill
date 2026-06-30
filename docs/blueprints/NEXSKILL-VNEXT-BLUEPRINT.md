# NexSkill vNext blueprint

**Status:** Approved direction - build spec needed
**Date:** 2026-06-30
**Owner:** Bahram Boutorabi

## One-line Product Shape

NexSkill is the development accelerator that selects the right skills, guides
agents through the work, and proves the result with deterministic local checks.

## Core Merge

```text
NexSkill = Skills + Skill Graph + Proof
```

| Layer | Source | Role |
|---|---|---|
| Thinking layer | `Real-Bimox/agent-skills` | Gives agents the right development discipline for planning, building, debugging, reviewing, documenting, and shipping. |
| Routing layer | current NexSkill/SkillDAG | Selects a small, relevant skill bundle and tracks dependencies, conflicts, specialization, and composition. |
| Proof layer | AutoDev deterministic patterns | Verifies repo state, selected-skill validity, handoff quality, closeout evidence, and policy hygiene. |

## Operating Rule

```text
Skills guide the work.
SkillDAG chooses the right skills.
Deterministic checks prove the result.
```

NexSkill may advise, route, check, and report. It does not automatically approve,
merge, release, or satisfy project owner gates.

## User Workflow

```text
developer describes work
  -> NexSkill reads repo config and task
  -> SkillDAG selects a bounded skill bundle
  -> agent works using those skills
  -> NexSkill runs deterministic checks
  -> NexSkill writes a short evidence report
  -> owner or project process decides what happens next
```

## MVP Commands

The first user-facing command set should be small:

```text
nexskill init
nexskill plan "<task>"
nexskill check --repo <path>
nexskill handoff --repo <path>
nexskill closeout --repo <path>
```

Current `skilldag` commands remain available during the transition.

## MVP Files

```text
.nexskill/config.json
.nexskill/skillgraph.json
.nexskill/evidence.jsonl
.nexskill/reports/latest.md
NEXSKILL.md
tools/nexskill/
```

The config names the repo's checks and policies. Evidence files are generated
from local runs. Reports summarize what passed, what failed, and what remains.

## First Build Slices

1. **Brand and compatibility**
   - Keep current SkillDAG behavior working.
   - Add `nexskill` as the forward-facing command name.
   - Update docs and package metadata carefully.

2. **Skill corpus import**
   - Import or reference `agent-skills` as the first curated corpus.
   - Add graph metadata for dependencies, conflicts, and useful compositions.
   - Report conflicts instead of silently choosing bad bundles.

3. **Deterministic proof MVP**
   - Add project readiness, skill-selection, handoff, closeout, and policy checks.
   - Make every check local, reviewable, and reproducible.
   - Treat failed checks as blockers or warnings, not as automatic repairs.

4. **Dogfood**
   - Run NexSkill on this repo.
   - Run NexSkill on one non-NexSkill repo, preferably NexHarness after the MVP is
     stable enough.
   - Record results in docs before claiming portability.

5. **NexHarness adapter**
   - Let NexHarness call NexSkill commands later.
   - Keep the adapter optional.
   - Do not give NexHarness merge, release, or owner-gate authority through this
     adapter.

## Trust Vocabulary

Use three simple evidence classes:

| Class | Meaning |
|---|---|
| `claimed` | Agent or user said it. Useful, not proof. |
| `derived` | Computed recommendation, such as a selected skill bundle. Advisory. |
| `trusted-local` | Deterministic local check passed. Still bounded to this repo/run. |

Do not use unqualified `trusted` for NexSkill output.

## Not Doing

- Not replacing AutoDev's factory gate.
- Not importing AutoDev's owner gates or role authority.
- Not auto-merging, tagging, releasing, or approving work.
- Not making NexHarness the source of truth.
- Not removing current SkillDAG research/reproduction material without a separate
  migration decision.

## Next Step

Create the first build-ready spec for Slice 1: brand and compatibility. It should
define the `nexskill` CLI wrapper, compatibility rules for `skilldag`, docs
updates, and verification commands.
