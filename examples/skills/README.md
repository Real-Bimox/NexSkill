# Example skill packages

Working `nexskill.skill.v1` skill packages you can copy into a project and use
immediately. Each package is a directory with a `manifest.json` and a `SKILL.md`
entrypoint, exactly matching what `nexskill init` seeds and what
`nexskill skill scaffold` produces.

## Packages

| Package | Stage | Notes |
|---|---|---|
| `reviewing.self-review` | verifying | Standalone self-review before closeout. |
| `closing.release-notes` | closing | Depends on `reviewing.self-review`; drafts release notes. |
| `closing.summary-only` | closing | Minimal closeout; declares `conflicts_with` `closing.release-notes`. |

Together they demonstrate a `depends_on` chain (`self-review` -> `release-notes`)
and a `conflicts_with` pair (`release-notes` vs `summary-only`).

## Try them

Copy any package into a configured skill source and validate:

```bash
nexskill init --repo .
cp -r examples/skills/reviewing.self-review .nexskill/skills/
nexskill skill validate --repo .
nexskill plan "review and close out a change" --repo .
```

To create your own from scratch instead, use the scaffold:

```bash
nexskill skill scaffold reviewing.checklist --repo . \
  --name "Review Checklist" \
  --summary "Runs a fixed review checklist over a change." \
  --stage verifying
```

See `docs/sdk/developing-skills.md` for the full developer guide and the
manifest schema reference in `docs/sdk/manifest-schema.md`.
