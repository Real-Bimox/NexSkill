# Skill pack template

This directory is the source template used by `nexskill skill scaffold`. It is
not itself a loadable skill package: it contains `${TOKEN}` placeholders that the
scaffold command substitutes before writing a concrete package.

Do not add this template directory to a NexSkill skill source. The registry
expects concrete `manifest.json` files with `nexskill.skill.v1`.

## Tokens

The scaffold substitutes these tokens across `manifest.json` and `SKILL.md`:

| Token | Source | Example |
|---|---|---|
| `${SKILL_ID}` | `--id`, else derived from the package name | `reviewing.checklist` |
| `${SKILL_NAME}` | `--name`, else a title-cased package name | `Review Checklist` |
| `${SKILL_SUMMARY}` | `--summary`, else a starter sentence | `...` |
| `${SKILL_STAGE}` | `--stage`, else `building` | `verifying` |

All four are required for a valid manifest. The scaffold fills any missing value
with a starter default and writes the result into `.nexskill/skills/<id>/`.

See `docs/sdk/developing-skills.md` for the full developer guide.
