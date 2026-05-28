# Reproducibility Checklist

This checklist verifies that the benchmark numbers can be reproduced from
a fresh clone following the instructions in `docs/reproducing.md`.

## Quick Smoke (≤10 min)

- [ ] `bash scripts/prepare_env.sh && bash scripts/setup.sh`
- [ ] `skilldag help` works
- [ ] `python -m unittest discover -s tests` passes

## Paper Table 1 — SkillsBench (scale=1000, ~hours)

- [ ] `SKILLDAG_SCALE=1000 bash scripts/run_skillsbench.sh`
- [ ] Compare `score_R_percent` vs `artifacts/expected/skillsbench_table1.json`
- [ ] Tolerance: ±3% (non-deterministic LLM agent + graph initialization)

## Paper Table 1 — ALFWorld (140 dev, ~30 min)

- [ ] `bash scripts/run_alfworld.sh` (MAX_GAMES=140)
- [ ] Compare `score_R_percent` vs `artifacts/expected/alfworld_table1.json`
- [ ] Tolerance: ±3%

## ALFWorld Train/Test Transfer (420+140+140, ~2h)

- [ ] `bash scripts/run_alfworld_traintest.sh`
- [ ] Compare `results/alfworld/traintest_*/summary.txt` vs `artifacts/expected/alfworld_traintest_metrics.json`
- [ ] Tolerance: ±2% per phase

## Cross-Scale Retrieval (requires all 4 scales run)

- [ ] Run each scale: `SKILLDAG_SCALE=N bash scripts/run_skillsbench.sh` for N in 200 500 1000 2000
- [ ] `python scripts/replay_queries.py --mode build-manifest --trials-dir results/... --output analysis/queries.json`
- [ ] `python scripts/replay_queries.py --mode cross-scale ...` → `analysis/cross_scale_scores.json`
- [ ] Compare Ret@5 vs `artifacts/expected/cross_scale_metrics.json`
- [ ] Tolerance: ±2% per scale

## 316-Query Cold-vs-Edited

- [ ] Run a traintest run to get `graph_after_train.json`
- [ ] `python scripts/replay_queries.py --mode edit-effect ...`
- [ ] Compare mean_rank vs `artifacts/expected/edit_effect_metrics.json`
- [ ] Tolerance: ±0.1 on mean_rank

## Key Paper Constants

| Constant | Value | Where |
|----------|-------|-------|
| K (top-k) | 5 | paper |
| D (neighbor depth) | 2 | paper |
| max_steps | 30 | paper |
| n_attempts | 2 | paper |
| reasoning_effort | high | paper |
| excluded task | mhc-layer-impl | paper |

## Non-Deterministic Notes

- Graph cold-start initialization uses embedding API + LLM pair classification — results may differ slightly
- Agent behavior (ALFWorld / SkillsBench) is non-deterministic by design
- Pre-built graphs are provided as the reproducible artifact; local re-initialization may differ from paper numbers