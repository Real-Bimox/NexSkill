# NexSkill

**NexSkill guides the work, selects the right skill path, and proves the result.**

NexSkill is a development accelerator. From inside any repository it selects a
bounded, ordered set of reusable skills for a task, guides the work along that
path, and proves the result with deterministic, dependency-light local checks.
It advises, routes, checks, and reports — it does not automatically approve,
merge, release, or satisfy owner gates.

## Install

NexSkill is a pure-Python package with no runtime dependencies and supports
Python ≥ 3.10.

```bash
# From a checkout of this repository:
pip install .

# Or build and install a wheel:
pip install build
python -m build --wheel
pip install dist/nexskill-*.whl
```

The installed package is self-contained: the built-in skill corpus and the
scaffold template ship inside the wheel, so `nexskill` works from any directory.

## Quickstart

```bash
nexskill init                              # create .nexskill/config.json + seed skills
nexskill plan "add a small repo change"    # bounded, deterministic skill path
nexskill check --repo .                    # run configured local checks
nexskill closeout --repo .                 # record closeout evidence + report
```

Every command accepts `--json` and returns one envelope:

```json
{ "ok": true, "schema_version": "nexskill.v1", "op": "plan", "result": {} }
```

Errors use the same shape with `ok: false`, a stable `UPPER_SNAKE` error code,
and a plain-language message.

## Add a skill

New skills require no core-code change. The fastest path is the scaffold, which
writes a valid package from the shipped template:

```bash
nexskill skill scaffold reviewing.checklist --repo . \
  --name "Review Checklist" \
  --summary "Runs a fixed review checklist over a change." \
  --stage verifying
nexskill skill validate --repo .
nexskill plan "review a change" --repo .
```

See [docs/sdk/developing-skills.md](docs/sdk/developing-skills.md) for the full
developer guide and [docs/sdk/manifest-schema.md](docs/sdk/manifest-schema.md)
for the manifest field reference. Working examples live in
[examples/skills/](examples/skills/).

## Commands

```text
nexskill init [--repo <path>] [--force]
nexskill plan "<task>" [--repo <path>] [--json]
nexskill check [--repo <path>] [--json]
nexskill closeout [--repo <path>] [--json]
nexskill skill list|validate [--repo <path>] [--json]
nexskill skill scaffold <name> [--id <id>] [--name <name>] [--summary <text>]
                          [--stage <stage>] [--force] [--repo <path>] [--json]
nexskill preflight [--repo <path>] [--expected-branch <name>]
                   [--expected-base <ref>] [--allow-untracked <glob>] [--json]
```

## Documentation

- [NEXSKILL.md](NEXSKILL.md) — product entry point: commands, quickstart,
  manifest format, planning, checks, and lane preflight.
- [docs/INDEX.md](docs/INDEX.md) — full documentation index.
- [docs/architecture.md](docs/architecture.md) — architecture and repository
  design.
- [AGENTS.md](AGENTS.md) — project guidance for agents working in this
  repository.

## Research provenance

NexSkill builds on a research reproduction of typed skill-graph retrieval for
LLM agents. That research code, benchmarks, and reproduction walkthrough remain
in this repository for provenance and are not part of the NexSkill product
surface:

- [docs/reproducing.md](docs/reproducing.md) — fresh-clone setup and benchmark
  walkthrough for the research reproduction.
- [docs/paper_reproduction.md](docs/paper_reproduction.md) — paper-aligned
  reproduction notes.
- `benchmarks/`, `analysis/`, `scripts/`, and the `src/skilldag/` package — the
  research library and benchmark integration.

If you use the underlying research, please cite:

```bibtex
@misc{bai2026skilldagselfevolvingtypedskill,
  title={SkillDAG: Self-Evolving Typed Skill Graphs for LLM Skill Selection at Scale},
  author={Tong Bai and Zhenglin Wan and Pengfei Zhou and Xingrui Yu and Wangbo Zhao and Yang You and Ivor W. Tsang},
  year={2026},
  eprint={2606.03056},
  archivePrefix={arXiv},
  primaryClass={cs.AI},
  url={https://arxiv.org/abs/2606.03056},
}
```

## License

MIT — see [LICENSE](LICENSE).
