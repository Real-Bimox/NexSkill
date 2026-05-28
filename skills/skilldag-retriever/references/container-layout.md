# Container Layout

Use this when wiring the retriever into a Docker or eval image.

## Expected Runtime

- `skilldag` CLI is installed on `PATH`
- SkillDAG package source is mounted at `/opt/skilldag/package`
- Per-task mutable graph data is mounted at `/var/lib/skilldag/runtime`
- Skill bodies are mounted at `/var/lib/skilldag/bodies`

The bundled SkillsBench template writes this wrapper:

```sh
#!/usr/bin/env sh
export PYTHONPATH="/opt/skilldag/package/src:/opt/skilldag/package:${PYTHONPATH:-}"
export SKILLDAG_SKILLS_DIR="${SKILLDAG_SKILLS_DIR:-/var/lib/skilldag/bodies}"
export SKILLDAG_GRAPH_PATH="${SKILLDAG_GRAPH_PATH:-/var/lib/skilldag/runtime/skillgraph.json}"
exec python3 -m skilldag "$@"
```

## Notes

- The per-task `skillgraph.json` must be a real copy, not a hardlink, so online
  edits do not propagate between concurrent tasks.
- Do not copy the whole skill library into native agent skill roots. Agents
  should discover skill bodies through `skilldag graph search` and
  `skilldag show`.
