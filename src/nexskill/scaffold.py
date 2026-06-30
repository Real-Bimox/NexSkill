"""NexSkill skill pack scaffolding.

Generates a concrete, valid ``nexskill.skill.v1`` skill package from the shipped
template by substituting ``${TOKEN}`` placeholders. The scaffold is the
authoring entry point for the skill pack SDK: it turns the template into a
package the registry can load immediately, with no core-code change.

Design notes:

- Boundary validation raises :class:`nexskill.contracts.NexSkillError` with a
  stable ``UPPER_SNAKE`` code, matching the rest of NexSkill.
- The generated manifest is validated with ``SkillManifest.from_dict`` before it
  is written, so a scaffolded package always loads.
- The scaffold never overwrites an existing package unless ``force`` is set.
- No third-party dependencies: only stdlib (``json`` / ``pathlib`` / ``re``).
- The CLI is a thin wrapper over :func:`scaffold_skill`; this module has no CLI
  or argparse imports, so contracts stay CLI-free.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .contracts import NexSkillError, SkillManifest, _ID_RE

#: Template directory shipped with the package, sibling of ``data/``.
TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates" / "skill_pack"

#: Default skill source directory relative to a repository root.
DEFAULT_SKILLS_DIR = Path(".nexskill") / "skills"

#: Default stage when none is given. ``building`` is the middle of the canonical
#: pipeline and is a safe, neutral default for a new skill.
DEFAULT_STAGE = "building"

#: Token names substituted across the template files.
TOKENS = ("SKILL_ID", "SKILL_NAME", "SKILL_SUMMARY", "SKILL_STAGE")

#: Starter summary when none is provided. Short, neutral, and self-describing.
DEFAULT_SUMMARY = "Describe what this skill does and when to use it."

#: Template files that are rendered (tokens substituted) on scaffold.
RENDERED_FILES = ("manifest.json", "SKILL.md")

_TOKEN_PATTERN = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


@dataclass(frozen=True)
class ScaffoldOptions:
    """Inputs resolved for a scaffold run.

    ``name`` is the human-readable skill name. ``summary`` is the one-line
    description. ``stage`` is the development stage the skill belongs to.
    ``id`` is validated to match the manifest id rule. ``force`` allows
    overwriting an existing package directory.
    """

    id: str
    name: str
    summary: str
    stage: str
    force: bool = False


@dataclass
class ScaffoldResult:
    """Outcome of a scaffold run."""

    package_dir: Path
    skill_id: str
    files_written: list[str] = field(default_factory=list)
    manifest: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, repo_root: Path | None = None) -> dict[str, Any]:
        pkg = self._rel(self.package_dir, repo_root)
        return {
            "package_dir": pkg,
            "skill_id": self.skill_id,
            "files_written": list(self.files_written),
            "manifest": dict(self.manifest),
        }

    @staticmethod
    def _rel(path: Path, repo_root: Path | None) -> str:
        if repo_root is not None:
            try:
                return str(path.relative_to(repo_root))
            except ValueError:
                pass
        return str(path)


# ---------------------------------------------------------------------------
# Resolution: turn raw CLI inputs into validated ScaffoldOptions
# ---------------------------------------------------------------------------


def derive_skill_id(name: str) -> str:
    """Derive a manifest-valid skill id from a human-readable name.

    Lowercases, replaces runs of non-alphanumeric characters with a single dot,
    and trims leading/trailing dots. Returns an empty string if the name yields
    nothing usable; the caller decides how to handle that.
    """
    if not isinstance(name, str):
        return ""
    squeezed = re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".")
    return squeezed


def title_case_name(name: str) -> str:
    """Turn a raw name token into a human-readable skill name.

    Splits on dots, hyphens, and underscores and title-cases each part so a
    scaffold id like ``reviewing.checklist`` becomes ``Review Checklist``.
    """
    if not isinstance(name, str) or not name.strip():
        return ""
    parts = [p for p in re.split(r"[.\-_\s]+", name.strip()) if p]
    return " ".join(p[:1].upper() + p[1:] for p in parts) if parts else ""


def resolve_options(
    name_arg: str,
    *,
    id: str | None = None,
    name: str | None = None,
    summary: str | None = None,
    stage: str | None = None,
    force: bool = False,
) -> ScaffoldOptions:
    """Resolve raw CLI inputs into validated :class:`ScaffoldOptions`.

    ``name_arg`` is the positional package name (e.g. ``reviewing.checklist``).
    The skill id defaults to it when ``--id`` is not given; the human-readable
    name defaults to a title-cased form of the id. Validation rejects ids that
    would not satisfy the manifest id rule.
    """
    if not isinstance(name_arg, str) or not name_arg.strip():
        raise NexSkillError("SCAFFOLD_INVALID_NAME", "skill name is required")

    raw_name = name_arg.strip()
    skill_id = (id or raw_name).strip()
    if not skill_id:
        raise NexSkillError("SCAFFOLD_INVALID_NAME", "skill id is required")
    if not _ID_RE.match(skill_id):
        raise NexSkillError(
            "SCAFFOLD_INVALID_ID",
            "skill id must be lowercase with dots, hyphens, or underscores and "
            f"start with an alphanumeric character; got {skill_id!r}",
        )

    display_name = (name or title_case_name(skill_id)).strip()
    if not display_name:
        # The id was purely punctuation and yielded no words; fall back to the id.
        display_name = skill_id

    display_summary = (summary or DEFAULT_SUMMARY).strip()
    display_stage = (stage or DEFAULT_STAGE).strip() or DEFAULT_STAGE

    return ScaffoldOptions(
        id=skill_id,
        name=display_name,
        summary=display_summary,
        stage=display_stage,
        force=bool(force),
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_text(text: str, values: dict[str, str]) -> str:
    """Substitute ``${TOKEN}`` placeholders in ``text``.

    Unknown tokens are left intact rather than erroring, so the template can
    carry documentation placeholders without breaking rendering. Only the four
    scaffold tokens are ever present in the shipped template.
    """

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return values.get(key, match.group(0))

    return _TOKEN_PATTERN.sub(repl, text)


def render_manifest(text: str, values: dict[str, str]) -> dict[str, Any]:
    """Render the manifest template and parse it to a dict.

    Parsing here (not just string substitution) lets us validate the result with
    ``SkillManifest.from_dict`` before writing anything to disk.
    """
    rendered = render_text(text, values)
    try:
        parsed = json.loads(rendered)
    except json.JSONDecodeError as exc:
        # Should be impossible with the shipped template; surface a stable code.
        raise NexSkillError(
            "SCAFFOLD_INVALID",
            f"rendered manifest is not valid JSON: {exc.msg}",
        ) from exc
    if not isinstance(parsed, dict):
        raise NexSkillError("SCAFFOLD_INVALID", "rendered manifest is not a JSON object")
    return parsed


# ---------------------------------------------------------------------------
# Scaffold
# ---------------------------------------------------------------------------


def _read_template(template_dir: Path, filename: str) -> str:
    path = template_dir / filename
    if not path.exists():
        raise NexSkillError(
            "SCAFFOLD_TEMPLATE_MISSING",
            f"skill pack template file not found: {filename}",
        )
    return path.read_text(encoding="utf-8")


def scaffold_skill(
    name_arg: str,
    repo_root: Path,
    *,
    id: str | None = None,
    name: str | None = None,
    summary: str | None = None,
    stage: str | None = None,
    force: bool = False,
    skills_dir: Path | str | None = None,
    template_dir: Path | None = None,
) -> ScaffoldResult:
    """Scaffold a concrete skill package from the shipped template.

    Writes ``manifest.json`` and ``SKILL.md`` into
    ``<repo_root>/<skills_dir>/<skill_id>/`` and returns the result. The
    generated manifest is validated with ``SkillManifest.from_dict`` before any
    file is written, so a scaffolded package is always loadable by the registry.

    Args:
        name_arg: Positional package name; defaults the skill id when ``id`` is
            not given.
        repo_root: Repository root the skill source is relative to.
        id: Override the skill id.
        name: Override the human-readable skill name.
        summary: Override the one-line summary.
        stage: Override the development stage.
        force: Overwrite an existing package directory.
        skills_dir: Skill source directory relative to ``repo_root`` (defaults
            to ``.nexskill/skills``).
        template_dir: Template directory (defaults to the shipped template).
    """
    options = resolve_options(
        name_arg, id=id, name=name, summary=summary, stage=stage, force=force
    )

    tdir = template_dir if template_dir is not None else TEMPLATE_DIR
    if not tdir.exists():
        raise NexSkillError(
            "SCAFFOLD_TEMPLATE_MISSING",
            f"skill pack template directory not found: {tdir}",
        )

    values = {
        "SKILL_ID": options.id,
        "SKILL_NAME": options.name,
        "SKILL_SUMMARY": options.summary,
        "SKILL_STAGE": options.stage,
    }

    # Render + validate the manifest before touching the filesystem so a bad
    # run leaves no partial package behind.
    manifest_text = _read_template(tdir, "manifest.json")
    manifest = render_manifest(manifest_text, values)
    # Re-validate through the canonical contract: this is what the registry will
    # do on load, so it must pass here.
    SkillManifest.from_dict(manifest)

    skill_text = _read_template(tdir, "SKILL.md")
    skill_rendered = render_text(skill_text, values)

    rel_skills = Path(skills_dir) if skills_dir is not None else DEFAULT_SKILLS_DIR
    package_dir = (repo_root / rel_skills / options.id).resolve()

    if package_dir.exists() and not options.force:
        raise NexSkillError(
            "SCAFFOLD_EXISTS",
            f"package already exists at {package_dir}. Use --force to overwrite.",
        )

    package_dir.mkdir(parents=True, exist_ok=True)
    files_written: list[str] = []
    (package_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    files_written.append("manifest.json")
    (package_dir / "SKILL.md").write_text(skill_rendered, encoding="utf-8")
    files_written.append("SKILL.md")

    return ScaffoldResult(
        package_dir=package_dir,
        skill_id=options.id,
        files_written=files_written,
        manifest=manifest,
    )
