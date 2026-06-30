"""NexSkill skill registry.

Discovers, validates, indexes, and caches skill package metadata from
configured local sources. The registry never loads full skill bodies into
command output — it operates on manifest metadata only, which keeps planning
bounded and cheap.

A skill package is a directory containing:

- ``manifest.json`` (``nexskill.skill.v1``); and
- the body file named by the manifest ``entrypoint`` (typically ``SKILL.md``).

Adding a future skill requires only dropping a valid package into a configured
source — no core-code change.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .contracts import SkillManifest, SkillSource


MANIFEST_FILENAME = "manifest.json"


@dataclass(frozen=True)
class LoadedSkill:
    """A validated skill package with its location."""

    manifest: SkillManifest
    package_dir: Path
    entrypoint_path: Path

    @property
    def id(self) -> str:
        return self.manifest.id

    def body(self) -> str:
        """Return the full skill body. Used only by explicit ``skill show``
        style commands — never by the planner or ``skill list``."""
        if not self.entrypoint_path.exists():
            return ""
        return self.entrypoint_path.read_text(encoding="utf-8", errors="ignore")


@dataclass
class RegistryLoadReport:
    """Outcome of loading all sources: which skills loaded, which failed, and
    how many sources were empty/missing."""

    loaded: list[str] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)
    sources_seen: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.skipped

    def to_dict(self) -> dict[str, Any]:
        return {
            "loaded": sorted(self.loaded),
            "skipped": [dict(s) for s in self.skipped],
            "sources_seen": list(self.sources_seen),
        }


class SkillRegistry:
    """Deterministic in-memory index of validated skill manifests.

    The index is sorted by skill id so every derived output (plan, report) is
    reproducible. Lookups by stage / tag / output / id are O(1)-ish over the
    parsed metadata.
    """

    def __init__(self) -> None:
        self._skills: dict[str, LoadedSkill] = {}

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, sources: list[SkillSource], repo_root: Path) -> tuple["SkillRegistry", RegistryLoadReport]:
        """Build a registry from configured sources rooted at ``repo_root``.

        Missing source directories are tolerated (recorded in the report as
        seen-but-empty); malformed manifests are skipped with a stable code and
        never enter the index.
        """
        registry = cls()
        report = RegistryLoadReport()
        for source in sources:
            src_path = (repo_root / source.path).resolve()
            report.sources_seen.append(source.path)
            if not src_path.exists() or not src_path.is_dir():
                continue
            registry._load_source(src_path, report)
        return registry, report

    def _load_source(self, src_path: Path, report: RegistryLoadReport) -> None:
        for entry in sorted(src_path.iterdir()):
            if not entry.is_dir():
                continue
            manifest_path = entry / MANIFEST_FILENAME
            if not manifest_path.exists():
                report.skipped.append(
                    {"package": entry.name, "code": "MANIFEST_MISSING", "reason": "no manifest.json"}
                )
                continue
            try:
                loaded = self._load_package(entry, manifest_path)
            except Exception as exc:  # validation error → skip, do not crash the registry
                code = getattr(exc, "code", "SKILL_INVALID")
                report.skipped.append(
                    {"package": entry.name, "code": code, "reason": str(exc)[:200]}
                )
                continue
            if loaded.id in self._skills:
                report.skipped.append(
                    {
                        "package": entry.name,
                        "code": "DUPLICATE_ID",
                        "reason": f"skill id {loaded.id!r} already loaded",
                    }
                )
                continue
            self._skills[loaded.id] = loaded
            report.loaded.append(loaded.id)

    def _load_package(self, package_dir: Path, manifest_path: Path) -> LoadedSkill:
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            from .contracts import NexSkillError
            raise NexSkillError("SKILL_INVALID", f"manifest.json is not valid JSON: {exc.msg}") from exc
        manifest = SkillManifest.from_dict(raw)
        entrypoint_path = package_dir / manifest.entrypoint
        if not entrypoint_path.exists():
            from .contracts import NexSkillError
            raise NexSkillError(
                "SKILL_INVALID",
                f"entrypoint {manifest.entrypoint!r} not found in package {package_dir.name}",
            )
        return LoadedSkill(manifest=manifest, package_dir=package_dir, entrypoint_path=entrypoint_path)

    # ------------------------------------------------------------------
    # Queries (metadata only — never return skill bodies)
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._skills)

    def ids(self) -> list[str]:
        return sorted(self._skills)

    def get(self, skill_id: str) -> LoadedSkill | None:
        return self._skills.get(skill_id)

    def require(self, skill_id: str) -> LoadedSkill:
        skill = self._skills.get(skill_id)
        if skill is None:
            from .contracts import NexSkillError
            raise NexSkillError("SKILL_NOT_FOUND", f"Skill not found: {skill_id}")
        return skill

    def by_stage(self, stage: str) -> list[LoadedSkill]:
        return sorted(
            (s for s in self._skills.values() if stage in s.manifest.stages),
            key=lambda s: s.id,
        )

    def by_tag(self, tag: str) -> list[LoadedSkill]:
        return sorted(
            (s for s in self._skills.values() if tag in s.manifest.tags),
            key=lambda s: s.id,
        )

    def by_output(self, output: str) -> list[LoadedSkill]:
        return sorted(
            (s for s in self._skills.values() if output in s.manifest.outputs),
            key=lambda s: s.id,
        )

    def all(self) -> list[LoadedSkill]:
        return sorted(self._skills.values(), key=lambda s: s.id)

    def index(self) -> list[dict[str, Any]]:
        """Deterministic metadata index (no bodies). Cached-quality: callers
        can keep this list and re-query without re-reading packages."""
        return [s.manifest.to_index_dict() for s in self.all()]

    def depends_on(self, skill_id: str) -> list[str]:
        skill = self.require(skill_id)
        return list(skill.manifest.depends_on)

    def conflicts_with(self, skill_id: str) -> list[str]:
        skill = self.require(skill_id)
        return list(skill.manifest.conflicts_with)
