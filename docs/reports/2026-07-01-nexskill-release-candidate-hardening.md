# NexSkill release-candidate hardening

Date: 2026-07-01
Branch: `nexskill/release-candidate-hardening`
Base: `origin/main` @ `8508576f3f507c5072f8e98906f731f1ea5f48a3`
Implementation commit: `7637fcb3778be4aea8bd26f8d595e324a606644a`

## What this round did

Made NexSkill installable, portable, and self-contained so the owner can make a
release decision. Before this round the wheel was named `skilldag`, shipped no
runtime resources, and a fresh install produced an empty skill corpus and a
crashing scaffold command. After this round a wheel installs cleanly outside the
source checkout and the full command sequence works.

| Feature / function | Lifecycle status |
|---|---|
| Built-in skills + scaffold template ship inside the wheel | Ready |
| Distribution renamed `skilldag` -> `nexskill`, single `nexskill` command | Ready |
| `--json` error path emits a clean envelope (no traceback leak) | Ready |
| Fresh-clone and wheel-install tests | Ready |
| Public docs lead with NexSkill; research kept as provenance | Ready |
| PyPI publication | Not done (owner decision; out of scope) |

## Changes

- **Resource packaging.** The built-in skill corpus and the scaffold template
  moved from repo-root `data/nexskill_skills/` and `templates/skill_pack/` into
  `src/nexskill/resources/{skills,templates/skill_pack}/`. They are resolved
  through `importlib.resources` (`src/nexskill/_resources.py`), never relative to
  a repository root. `pyproject.toml` declares them as package data so they ship
  in the wheel.
- **Distribution identity.** Distribution renamed `skilldag` -> `nexskill`
  (version unchanged at `0.1.0`). The legacy `skilldag` console script is no
  longer installed; `nexskill` is the only command. The legacy `skilldag` Python
  module still ships for provenance and compatibility, and its tests
  (`python -m skilldag ...`) are unaffected.
- **CLI robustness.** `_run_command` no longer lets `_Exit` escape the
  `NexSkillError` handler, so `--json` errors print one error envelope and exit
  1 instead of a Python traceback.
- **Tests.** Added `tests/test_packaging.py`: resource resolution, a guard that
  no package module uses a repo-root `parents[2]` lookup, a fresh-clone source
  run (tracked files only), and a wheel build/install in a clean venv that runs
  the full command sequence outside the source checkout.
- **Docs.** `README.md` and `docs/INDEX.md` now lead with NexSkill as the
  product; the research reproduction is preserved under a clearly labeled
  "Research provenance" section.

## Verification

All commands run from the branch checkout in an isolated virtualenv
(Python 3.14.6).

### Source-checkout tests

```
python -m pip install -e .
python -m pytest -q
```

Result: **196 passed** (was 188 before this round; +8 new packaging/CLI tests).

### Wheel build + clean-environment install

```
python -m build --wheel --outdir dist
# -> dist/nexskill-0.1.0-py3-none-any.whl
python -m venv /tmp/cleanenv
/tmp/cleanenv/bin/python -m pip install --no-index --no-deps dist/nexskill-0.1.0-py3-none-any.whl
```

Verified:
- Wheel filename is `nexskill-0.1.0-py3-none-any.whl`.
- Wheel contains `nexskill/resources/skills/**` and
  `nexskill/resources/templates/skill_pack/**`.
- Only the `nexskill` console script is installed (no `skilldag` script).

### CLI smoke test from outside the repo

In a temporary directory with no access to the source tree, using the installed
console script:

```
nexskill init --repo . --json        # seeds 4 skills (building.implementation,
                                     #   closing.handoff, planning.task-breakdown,
                                     #   verifying.testing)
nexskill plan "..." --repo . --json  # ok, 4 steps
nexskill check --repo . --json       # status: warning (advisory, non-blocking)
nexskill closeout --repo . --json    # ok
nexskill skill scaffold reviewing.checklist --repo . --json  # ok
nexskill skill validate --repo . --json                      # valid
nexskill preflight --repo . --json   # well-formed envelope (ok=false: fresh repo
                                     #   has untracked .nexskill artifacts)
```

This sequence is also asserted automatically by
`tests/test_packaging.py::WheelInstallTests`.

### Naming / source-containment scan

- `src/nexskill/**.py`: no forbidden source names except the
  `FORBIDDEN_SOURCE_NAMES` denylist constant in `report.py`, which is the
  guardrail itself.
- `NEXSKILL.md`: clean.
- `README.md`: source names (`SkillDAG`, citation) appear only in the
  "Research provenance" section, permitted under AGENTS.md §2 for
  provenance/citation.
- Generated reports/evidence excluded forbidden names (integration scan tests).

### Attribution scan

No `co-authored-by`, `generated-by`, machine-attribution trailers, or
attribution emojis in the package source or product docs. The implementation
commit message has no attribution trailer.

### Lint

`ruff check` is clean on all files changed this round. Five pre-existing `ruff`
findings remain in untouched research tests (`tests/test_contracts.py`,
`tests/test_report.py`) — multi-statement lines and an unused import — and are
out of scope for this round.

## Is wheel/install portability proven?

Yes. The wheel builds with the correct name, bundles all runtime resources,
installs in a clean virtualenv with no source-tree access, and runs the full
`init -> plan -> check -> closeout -> skill scaffold -> preflight` sequence from
an unrelated working directory. This is proven both manually and by an automated
test in the suite.

## Remaining release blockers

None that block the owner's release decision on this branch. Smaller items the
owner may want addressed first:

1. **Pre-existing lint debt** in two research test files (above). Cosmetic;
   does not affect the product.
2. **Package metadata polish (optional).** `authors` still lists the research
   paper authors and `keywords`/`classifiers` are research-oriented. Left
   conservative per instructions; the owner may want product-specific metadata
   before any publication.
3. **No `LICENSE`/author review for redistribution.** The wheel is installable
   locally; publishing anywhere public is a separate owner decision.

## Owner decision needed before tag/release

- Approve the distribution rename `skilldag` -> `nexskill` as the released
  package identity (applied on this branch; not yet tagged or published).
- Decide whether to publish (and where) — nothing has been tagged, released, or
  pushed to any index. Per project policy, tag and GitHub Release require
  explicit owner approval.
- Confirm whether package metadata (`authors`, `keywords`, `classifiers`) should
  be updated to product-specific values before any publication.

Not done, per instructions: no merge to `main`, no tag, no release, no deletion
of legacy/research source or docs.
