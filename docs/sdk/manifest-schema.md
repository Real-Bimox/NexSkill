# NexSkill skill manifest schema reference

Status: Current
Date: 2026-06-30
Owner: Bahram Boutorabi

Reference for the `nexskill.skill.v1` skill manifest. The schema is defined and
enforced by `nexskill.contracts.SkillManifest.from_dict`; this document is the
human-readable mirror of that contract. When the two disagree, the code is the
source of truth.

Schema versions are additive. A future `nexskill.skill.v2` would be a new
schema version validated separately, not a mutation of this one. Unknown fields
in a `v1` manifest are preserved verbatim (forward compatibility) but never
interpreted.

## File and location

- Filename: `manifest.json`
- Location: the root of a skill package directory under a configured skill
  source (default `.nexskill/skills/<skill-id>/manifest.json`).
- Format: UTF-8 JSON, a single object.

## Fields

### Required fields

Each required field must be present and non-empty (a present-but-empty string is
treated as missing).

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | Must be exactly `nexskill.skill.v1`. |
| `id` | string | Lowercase, starts alphanumeric, then `a-z0-9._-` only. Unique across all loaded packages. |
| `name` | string | Human-readable name. Non-empty. |
| `summary` | string | One-line description. Non-empty. |
| `stages` | string[] | Non-empty list of development stages (e.g. `planning`, `building`, `verifying`, `closing`). |
| `entrypoint` | string | Body filename within the package (typically `SKILL.md`). Must exist. |

### Optional fields

Optional fields default to empty lists when omitted.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `inputs` | string[] | `[]` | Artifacts/concepts this skill consumes. Used by planning overlap scoring. |
| `outputs` | string[] | `[]` | Artifacts/concepts this skill produces. Used by planning overlap scoring. |
| `depends_on` | string[] | `[]` | Skill ids that are prerequisites; the planner expands them transitively. |
| `conflicts_with` | string[] | `[]` | Skill ids that should not run alongside this one; surfaced as advisory signals. |
| `tags` | string[] | `[]` | Free-form tags; used by planning overlap scoring and `by_tag` queries. |

### Unknown fields

Any other top-level key is preserved verbatim in the manifest's `unknown` map
and is never interpreted. This lets a manifest carry project-specific metadata
without breaking forward compatibility. Do not rely on unknown fields for
behavior - they may be ignored or, in a future major schema, redefined.

## Minimal valid manifest

```json
{
  "schema_version": "nexskill.skill.v1",
  "id": "reviewing.checklist",
  "name": "Review Checklist",
  "summary": "Runs a fixed review checklist over a change.",
  "stages": ["verifying"],
  "entrypoint": "SKILL.md"
}
```

## Full manifest

```json
{
  "schema_version": "nexskill.skill.v1",
  "id": "closing.release-notes",
  "name": "Release Notes",
  "summary": "Drafts concise release notes from the verified changes.",
  "stages": ["closing"],
  "inputs": ["code_change", "review_notes"],
  "outputs": ["release_notes"],
  "depends_on": ["reviewing.self-review"],
  "conflicts_with": [],
  "tags": ["development", "closing", "example"],
  "entrypoint": "SKILL.md"
}
```

## Validation behavior

`SkillManifest.from_dict` validates at the boundary: a malformed manifest raises
`NexSkillError("SKILL_INVALID", ...)` and never enters the registry. The
registry layer maps filesystem-level problems to their own codes:

| Layer | Code | When |
|---|---|---|
| Manifest parse | `SKILL_INVALID` | Bad JSON, wrong schema version, missing/empty required field, malformed id, empty `stages`, wrong-type list. |
| Package load | `SKILL_INVALID` | `manifest.json` is not valid JSON, or the `entrypoint` file is missing. |
| Source scan | `MANIFEST_MISSING` | A package directory has no `manifest.json`. |
| Source scan | `DUPLICATE_ID` | A skill id was already loaded from another package. |

A skipped package never aborts a registry load; it is recorded in the load
report and the remaining packages still load. `nexskill skill validate` exits
non-zero if any package was skipped.

## id rules in detail

The `id` must match `^[a-z0-9][a-z0-9._-]*$`:

- Starts with a lowercase letter or digit.
- Continues with lowercase letters, digits, dots, hyphens, or underscores.
- No spaces, no uppercase, no leading punctuation.

Convention is `<stage-or-area>.<name>`, for example `planning.task-breakdown`,
`building.implementation`, `reviewing.checklist`. The id is the durable identity
of a skill; renaming it is a breaking change for any `depends_on` /
`conflicts_with` that references it.

## See also

- [Developing skills](developing-skills.md) - the developer guide and scaffold
  command.
- [Examples](../../examples/skills/) - three working skill packages.
- `src/nexskill/contracts.py` - the authoritative `SkillManifest` contract.
