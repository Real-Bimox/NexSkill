# SkillDAG

Open-source reproduction repository for **SkillDAG: Self-Evolving Typed Skill Graphs for LLM Skill Selection at Scale**.

This repo is for **benchmark rerun reproduction**:

- prepare the environment
- download required benchmark assets
- run ALFWorld / SkillsBench benchmarks
- score and verify against expected paper numbers

## What is in this repo

- `src/skilldag/` — SkillDAG library and CLI
- `scripts/` — setup, data download, benchmark launchers, replay tools
- `benchmarks/` — ALFWorld + SkillsBench integration code
- `analysis/` — scoring and post-hoc analysis helpers
- `docs/reproducing.md` — fresh-clone walkthrough
- `docs/paper_reproduction.md` — claim → command → verification contract
- `artifacts/expected/` — expected paper-aligned metrics for verification

## Quickstart

```bash
git clone https://github.com/Ericbai06/SkillDAG.git
cd SkillDAG
bash scripts/prepare_env.sh
# fill API keys in .env
bash scripts/setup.sh
```

`bash scripts/setup.sh` is the main setup entrypoint. It installs dependencies,
downloads published SkillDAG graph artifacts, fetches skill libraries and
SkillsBench tasks, and prepares the ALFWorld skill pool.

## End-to-end benchmark entrypoints

### SkillsBench smoke

```bash
SKILLDAG_SCALE=200 SKILLDAG_WORKERS=3 bash scripts/run_skillsbench.sh
```

### ALFWorld smoke

```bash
MAX_GAMES=10 bash scripts/run_alfworld.sh
```

### Paper-scale runs

```bash
SKILLDAG_SCALE=1000 SKILLDAG_WORKERS=5 bash scripts/run_skillsbench.sh
bash scripts/run_alfworld.sh
bash scripts/run_alfworld_traintest.sh
```

## Verification

See:

- `docs/reproducing.md`
- `docs/paper_reproduction.md`
- `REPRODUCIBILITY_CHECKLIST.md`

## Notes

- Primary documented backbone: OpenAI direct via `gpt-5.2-codex` defaults in `.env.example`
- Optional alternative backbone: OpenRouter
- Figure/table generation for the paper is **not** in scope for this repo
- This repo is for rerunning benchmarks, not for replaying precomputed paper tables only

## License

MIT
