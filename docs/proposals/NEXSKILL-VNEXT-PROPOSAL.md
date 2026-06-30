# Proposal - NexSkill vNext

**Status:** APPROVED DIRECTION - BUILD SPEC NEEDED
**Lifecycle:** DRAFT -> APPROVED DIRECTION -> SPEC -> IMPLEMENTED
**Established:** 2026-06-30
**Owner:** Bahram Boutorabi
**Triage tier:** **T2** - combines three independent capability sources into a
new product/version contract: `Real-Bimox/NexSkill`, `Real-Bimox/agent-skills`,
and portable AutoDev deterministic components.
**Decision anchor:** [`0001-nexskill-vnext-approved-direction.md`](../decisions/0001-nexskill-vnext-approved-direction.md)

---

## 1. Summary

Create **NexSkill vNext** as the next version of the current NexSkill product by
combining three core elements:

1. `Real-Bimox/agent-skills` - the engineering lifecycle skill corpus.
2. `Real-Bimox/NexSkill` - the current SkillDAG product spine: typed skill graph,
   dependency-aware retrieval, `skilldag` CLI, and online edge editing.
3. AutoDev deterministic components - portable checks and evidence patterns that
   prove whether development work is ready, not merely claimed.

The product promise:

> NexSkill selects the right skills, tells agents how to use them, and proves the
> development result with deterministic project evidence.

This proposal is now an approved product direction. It does not implement code,
change AutoDev authority, merge the external repos, activate NexHarness, or grant
any auto-merge/release/owner-gate authority.

## 2. Source inputs inspected

| Source | Current inspected state | Role in NexSkill vNext |
|---|---|---|
| `Real-Bimox/agent-skills` | GitHub HEAD `aba7c4e9695c363e65cb59effe926c7f1d1abe3d`; 24 installed skills | Lifecycle skill corpus and operating disciplines |
| `Real-Bimox/NexSkill` | GitHub HEAD `440068a6b6af6a20cbff2efd107969e317ab65f8`; current repo presents as SkillDAG | Product home and skill-graph/retrieval spine |
| AutoDev | Current AutoDev `origin/main` at proposal time | Deterministic checks, evidence vocabulary, trust-boundary patterns |

The local `/Users/bahramboutorabi/local-repos/NexSkill` checkout now tracks the
GitHub repo `Real-Bimox/NexSkill`, which is the product source of truth.

## 3. Problem

Agent skill libraries solve only one part of the development loop. They help the
agent behave better, but they do not decide which skills should be loaded from a
large library, and they do not independently prove that the resulting work is
safe or ready.

Current NexSkill/SkillDAG solves another part: it models skill selection as a
typed graph with dependency, composition, similarity, specialization, and
conflict edges. That gives a better retrieval spine, but it is not yet a complete
development acceleration product for ordinary repositories.

AutoDev solves a third part: deterministic proof. It separates what an agent
claims from what the repository can compute.

NexSkill vNext should merge these strengths into one product:

- graph-aware skill selection;
- high-quality lifecycle skill content;
- deterministic development evidence.

## 4. Goals

1. Rebrand the next version of the current SkillDAG-based NexSkill as
   **NexSkill**.
2. Use `Real-Bimox/NexSkill` as the product home.
3. Bring `Real-Bimox/agent-skills` into NexSkill as the first curated lifecycle
   skill corpus.
4. Preserve SkillDAG's typed graph and CLI concepts as the skill-selection core.
5. Add an AutoDev-inspired deterministic evidence layer for project readiness,
   skill-selection validity, handoff quality, closeout quality, and policy
   hygiene.
6. Keep skills and graph outputs advisory until deterministic checks prove the
   relevant claim.
7. Make NexSkill portable to any development repo without requiring full AutoDev
   adoption.
8. Prepare a clean future path for NexHarness to run NexSkill as a development
   skill/runtime service.

## 5. Non-goals

- No replacement of AutoDev's factory gate.
- No wholesale import of AutoDev's owner rules, role manuals, or factory
  authority into NexSkill. A NexSkill-owned `AGENTS.md` may adapt AutoDev's
  portable operating discipline.
- No Active Routing, auto-merge, release, protected-branch, or owner-gate
  authority.
- No NexHarness runtime integration in this proposal.
- No dependency on AutoDev as a runtime package.
- No claim that graph retrieval alone proves a skill choice was correct.
- No automatic mutation of a target repository beyond explicitly requested,
  reviewable install/configuration actions.
- No deletion or overwrite of the current SkillDAG research/reproduction
  material without a separate migration decision.

## 6. Right-home assessment

| Capability | Right home | Rationale |
|---|---|---|
| Product brand and user-facing package | NexSkill | This is the next version of the current NexSkill product. |
| Skill graph, search, and online graph editing | NexSkill | Existing SkillDAG code is already the natural spine. |
| Lifecycle skills and command/persona patterns | NexSkill vendor/import from `agent-skills` | Skills are reusable capability, not AutoDev authority. |
| Deterministic proof patterns | NexSkill portable implementation, derived from AutoDev patterns | Generic proof belongs in a reusable product; AutoDev-specific authority stays in AutoDev. |
| AutoDev factory gate and owner policy | AutoDev only | These are AutoDev trust-boundary and governance surfaces. |
| Runtime session hosting and learning loops | Future NexHarness adapter | NexHarness is the likely runtime host, but not part of this proposal. |

This follows Decision 0001: the reusable product lives in NexSkill; AutoDev
keeps its own governance and trusted gate.

## 7. Proposed design

### 7.1 Product layers

NexSkill vNext should have five layers:

| Layer | Source | Responsibility |
|---|---|---|
| Skill corpus | `agent-skills` | High-quality lifecycle skills, command mappings, personas, and references |
| Skill graph | current NexSkill/SkillDAG | Typed graph, search, dependencies, conflicts, composition, online edge edits |
| Evidence layer | AutoDev-inspired portable scripts | Project readiness, handoff, closeout, policy, and attribution checks |
| Install/config layer | NexSkill | Repo-local config, skill bundle installation, generated reports |
| Runtime adapter layer | future NexHarness | Optional session hosting, trace capture, and workflow execution |

### 7.2 Core workflow

NexSkill should support this user flow:

```text
developer asks for work
  -> NexSkill retrieves a bounded skill bundle
  -> agent follows the selected skills
  -> NexSkill runs deterministic project checks
  -> NexSkill records a short evidence report
  -> repo owner sees what was done, what passed, and what remains
```

### 7.3 CLI shape

The implementing spec should preserve current `skilldag` compatibility while
introducing user-facing `nexskill` commands:

```text
nexskill search "<task>"
nexskill show <skill-id>
nexskill add <skill-id> --to <repo>
nexskill check --repo <repo>
nexskill handoff --repo <repo>
nexskill closeout --repo <repo>
nexskill graph propose-edge ...
nexskill graph edit-edge ...
```

Compatibility rule: existing `skilldag` commands should remain available through
an alias or compatibility module for at least one transition release.

### 7.4 Deterministic evidence MVP

The first proof layer should be deliberately small:

| Check | Purpose | AutoDev source pattern |
|---|---|---|
| project readiness | Confirms the target repo has rules, commands, test entry points, and clean branch state | core readiness preflight, sync safety |
| skill selection | Confirms selected skills exist, graph edges are valid, and conflicts are reported | component/capability ledger validation |
| handoff quality | Confirms scope, changed files, verification, risks, and next step are present | handoff and review contract checks |
| closeout quality | Runs configured project checks and records pass/fail evidence | factory-cycle/report pattern |
| policy hygiene | Blocks unwanted attribution and obvious secret markers where configured | attribution guard and policy checks |

These checks produce local project evidence only. They do not approve merges.

### 7.5 Trust classes

NexSkill should adopt a simple trust vocabulary inspired by AutoDev:

| Trust class | Meaning | Example |
|---|---|---|
| `claimed` | Agent/user supplied; useful but not proof | "I used these skills" |
| `derived` | Computed from claimed/trusted inputs; advisory | recommended skill bundle |
| `trusted-local` | Deterministic local check passed | closeout check exit 0 |

NexSkill should avoid the word `trusted` without a qualifier, because project
owners may have different governance requirements. AutoDev can map
`trusted-local` into its own stricter evidence system only through an approved
adapter.

### 7.6 Interface rules

NexSkill should keep command interfaces stable and hard to misuse:

- existing `skilldag` command behavior remains observable compatibility during
  the transition release;
- new `nexskill` commands return a consistent JSON envelope when `--json` is
  passed:

```json
{
  "ok": true,
  "schema_version": "nexskill.v1",
  "op": "check",
  "result": {}
}
```

- errors use the same envelope shape with `ok: false`, machine-readable
  `error.code`, and human-readable `error.message`;
- new result fields are additive and optional until a schema version is bumped;
- target repository input is validated at the boundary before checks read,
  write, or report on it;
- raw transcripts, secrets, private prompts, and local account details are never
  valid report fields.

## 8. Data and file contracts

The implementing spec should define these portable surfaces:

```text
.nexskill/config.json
.nexskill/skillgraph.json
.nexskill/evidence.jsonl
.nexskill/reports/latest.json
.nexskill/reports/latest.md
tools/nexskill/
NEXSKILL.md
```

Contract expectations:

- `.nexskill/config.json` declares project commands, policy checks, skill
  sources, and write targets.
- `.nexskill/skillgraph.json` is the repo-local graph or pointer to the active
  graph.
- `.nexskill/evidence.jsonl` records append-only local evidence events.
- `.nexskill/reports/latest.*` are generated outputs and must be reproducible
  from config, graph, and evidence.
- `NEXSKILL.md` is the repo-local human/agent entry point.
- `tools/nexskill/` is the default namespaced install location to avoid
  collisions.

## 9. Migration from current NexSkill

Phase the work so the current SkillDAG value is preserved:

| Phase | Outcome | Stop / partial-failure behavior | Authority |
|---|---|---|---|
| Phase 0 - Proposal and inventory | Current NexSkill, `agent-skills`, and AutoDev portable components inventoried | stop at proposal if source inventory conflicts | no behavior change |
| Phase 1 - Brand and compatibility | Package and docs introduce NexSkill vNext while preserving `skilldag` compatibility | keep `skilldag` as the working command if `nexskill` wrapper fails | repo-local only |
| Phase 2 - Agent-skills corpus | `agent-skills` becomes the first curated corpus with graph metadata | corpus import may be retried; graph output must fail closed on invalid edges | advisory retrieval |
| Phase 3 - Evidence MVP | portable readiness, handoff, closeout, and policy checks ship | failed checks report blockers; they do not approve or repair automatically | local proof only |
| Phase 4 - Dogfood | validate in AutoDev and one non-AutoDev repo | failed dogfood remains evidence; no target repo authority expands | evidence gathering |
| Phase 5 - NexHarness adapter | optional runtime host calls NexSkill through stable commands | adapter can be disabled without changing NexSkill core behavior | no merge/owner authority |

## 10. Testing and validation strategy

The build-ready spec should include:

- graph tests for dependency/conflict traversal on the `agent-skills` corpus;
- compatibility tests for existing `skilldag` CLI commands;
- deterministic tests for each evidence MVP check;
- fixture repos for clean, missing-config, failed-test, conflicted-skill, and
  incomplete-handoff cases;
- one AutoDev dogfood run labeled as local evidence only;
- one NexHarness or other repo trial to prove portability.

## 11. Owner decision points

Approved on 2026-06-30 by owner direction:

1. **NexSkill vNext** is the product direction that merges the three capability
   sources named in this proposal.
2. `Real-Bimox/NexSkill` is the product home, with AutoDev contributing patterns
   and portable components rather than becoming a runtime dependency.
3. The first MVP scope is SkillDAG compatibility, the `agent-skills` corpus, and
   the five deterministic evidence checks in §7.4.
4. NexSkill vNext has no AutoDev merge, owner-gate, Active Routing, release, or
   protected-branch authority.
5. NexSkill should carry a project-owned `AGENTS.md` adapted from AutoDev's
   reusable operating discipline.

## 12. Open questions

- Should the first implementation rename the Python package from `skilldag` to
  `nexskill`, or ship `nexskill` as a wrapper while leaving `skilldag` as the
  internal module for one transition release?
- Should `agent-skills` be vendored into NexSkill, referenced as a git source,
  or imported through an installer/update command?
- Which non-AutoDev repo should be the first portability trial after AutoDev
  dogfooding?

## 13. Touched surfaces if approved

| Surface | Expected change | Repo |
|---|---|---|
| `README.md` and package metadata | brand current SkillDAG as NexSkill vNext with compatibility notes | NexSkill |
| `src/skilldag/` or future `src/nexskill/` | compatibility-preserving CLI/package evolution | NexSkill |
| `skills/` | add or import curated `agent-skills` corpus and graph metadata | NexSkill |
| `.nexskill/` fixtures | define config/evidence/report contracts | NexSkill |
| portable check scripts | implement evidence MVP | NexSkill, derived from AutoDev patterns |
| AutoDev docs | track this proposal and future dogfood evidence only | AutoDev |

## 14. Quality Gate

### 14.1 Canonical contract surfaces

| Surface | Canonical? | Mirrors / references | Checked |
|---|---:|---|---|
| this proposal | yes | product-direction contract for NexSkill vNext | [x] |
| `Real-Bimox/NexSkill` current SkillDAG repo | yes, external source | product home and graph spine; inspected at `440068a6b6af6a20cbff2efd107969e317ab65f8` | [x] |
| `Real-Bimox/agent-skills` | yes, external source | lifecycle skill corpus; inspected at `aba7c4e9695c363e65cb59effe926c7f1d1abe3d` | [x] |
| AutoDev deterministic components | yes, source patterns only | AutoDev authority remains canonical in AutoDev; NexSkill receives portable derivatives only | [x] |
| future `.nexskill/*` contracts | yes, after spec | proposed in §8; schema details deferred to build-ready spec | [x] |
| future NexHarness adapter | no | optional future runtime integration; not part of this proposal | [N/A - deferred integration surface] |

### 14.2 State / Handoff Invariants

- [N/A - no queue entry shape introduced by this proposal] Every queue entry shape has one parser and one dispatch behavior.
- [x] Every writer has an explicit allowlist - §6 and §13 keep product writes in NexSkill and AutoDev authority in AutoDev.
- [x] Every multi-step handoff defines partial-failure behavior - §9 phases preserve compatibility and stop before runtime authority.
- [x] Every durable artifact has ownership, collision, recovery, and deletion/supersede semantics - §8 names repo-local `.nexskill/*` artifacts; §13 names owning repos.
- [x] Every repeated rule names its canonical source - §6 ties right-home placement to Decision 0001 and keeps AutoDev-specific authority in AutoDev.

### 14.3 Quality Checklist

- [x] Touched surfaces listed, including conditional surfaces (§13)
- [x] Canonical source for each rule declared (§14.1)
- [x] Change type classified (T2; product/version contract across three sources)
- [x] Minimal-scope traceability included for abstractions, features, dependencies, and new surfaces (§4, §5, §7)
- [N/A - no copyable implementation prescriptions beyond illustrative CLI shape] Copyable implementation prescriptions contain no known-bad text
- [x] Claim-to-evidence coverage table included for inherited requirements (§14.4)
- [x] Proof type classified for every test or verification item (§7.5, §10)
- [x] Writer authority table included (§6, §13)
- [x] Read/write fallback defined (§9 compatibility and §8 generated/report surfaces)
- [x] Tests map to all P1/P2 risks (§10)
- [N/A - CI is not touched by this proposal] CI classified as signal-only or merge-blocking
- [N/A - no hot-reload surface touched] Hot-reload safety proven or schema bump declared
- [x] State machine included (§9 migration phases)
- [x] Partial failure matrix included (§9 phase-by-phase stop points)
- [N/A - no data migration is performed by this proposal] Migration contract included, if applicable

### 14.4 Claim-to-evidence coverage

| Claim | Evidence source | Proof type | Status |
|---|---|---|---|
| `agent-skills` exposes 24 lifecycle skills | local checkout and installed skill inventory at `aba7c4e9695c363e65cb59effe926c7f1d1abe3d` | source inspection | supported |
| current NexSkill repo is SkillDAG-shaped | read-only clone of `Real-Bimox/NexSkill` at `440068a6b6af6a20cbff2efd107969e317ab65f8` | source inspection | supported |
| AutoDev deterministic components should remain authority-bound inside AutoDev | Decision 0001 and AutoDev source-pattern review | governance evidence | supported |
| NexSkill vNext needs a spec before implementation | AutoDev proposal/spec lifecycle in `AGENTS.md` | process rule | supported |

### 14.5 Review Findings

| ID | Severity | Location | Finding | Status | Resolution / Evidence |
|---|---|---|---|---|---|
| P_-001 | | | | open | |

### 14.6 Direction Approval Record

- [x] Owner approved the product direction in Decision 0001.
- [x] AutoDev authority, owner gates, merge authority, release authority, and
  Active Routing remain excluded.
- [x] NexSkill-owned `AGENTS.md` adaptation is allowed.
- [ ] Build-ready implementation spec created.
- [ ] Implementation verification run.
