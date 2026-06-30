# Skill pack validation fixtures

Static skill-package fixtures used by the scaffold and registry tests. They are
**not** under a configured NexSkill skill source, so a normal `nexskill init`
project never loads them; tests point a throwaway registry at this directory on
purpose.

## Layout

| Path | Expected registry outcome |
|---|---|
| `valid.minimal/` | Loads; appears in the index. |
| `invalid/missing-field/` | Skipped, code `SKILL_INVALID` (empty `summary`). |
| `invalid/bad-id/` | Skipped, code `SKILL_INVALID` (invalid `id`). |
| `invalid/no-manifest/` | Skipped, code `MANIFEST_MISSING` (no `manifest.json`). |

These mirror the validation codes produced by
`nexskill.contracts.SkillManifest.from_dict` and
`nexskill.registry.SkillRegistry._load_source`, so tests can assert on the exact
skip code without depending on internal wording.

## Duplicate-id fixture

There is no static duplicate-id directory: a duplicate is created in-test by
copying `valid.minimal/` to a second directory with the same manifest `id`, then
asserting that the registry skips the second one with code `DUPLICATE_ID`. This
keeps the static fixtures free of two packages that share an id (which would
break any other test scanning the same tree).
