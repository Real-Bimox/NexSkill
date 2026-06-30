"""NexSkill core contracts.

Stable dataclasses and helpers for commands, skill manifests, plan results,
check results, evidence events, reports, and errors.

Contracts first, implementation second. Every public NexSkill command emits one
JSON envelope; every error uses the same envelope with a stable
``UPPER_SNAKE`` code and plain-language message. This module never depends on
CLI rendering.

Schema versions are additive and explicit:

- ``nexskill.v1``           command JSON envelope
- ``nexskill.config.v1``    ``.nexskill/config.json``
- ``nexskill.skill.v1``     skill package manifests
- ``nexskill.evidence.v1``  ``.nexskill/evidence.jsonl`` events
- ``nexskill.report.v1``    ``.nexskill/reports/latest.json``
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Schema versions
# ---------------------------------------------------------------------------

ENVELOPE_SCHEMA_VERSION = "nexskill.v1"
CONFIG_SCHEMA_VERSION = "nexskill.config.v1"
SKILL_SCHEMA_VERSION = "nexskill.skill.v1"
EVIDENCE_SCHEMA_VERSION = "nexskill.evidence.v1"
REPORT_SCHEMA_VERSION = "nexskill.report.v1"
GRAPH_SCHEMA_VERSION = "nexskill.graph.v1"

# ---------------------------------------------------------------------------
# Graph relationship vocabulary
# ---------------------------------------------------------------------------
#
# NexSkill plans over a small typed-edge graph. Manifest declarations supply the
# baseline edges (``depends_on``, ``conflicts_with``); an optional, NexSkill-owned
# overlay (``.nexskill/graph.json``) can add the richer relationships below. The
# vocabulary is intentionally the same five typed relations used across NexSkill
# so a single mental model covers manifests and overlays alike.

#: Every relationship type the NexSkill graph understands.
GRAPH_EDGE_TYPES = (
    "depends_on",
    "composes_with",
    "specializes",
    "similar_to",
    "conflicts_with",
)

#: Relationships that are direction-independent (A~B implies B~A).
GRAPH_SYMMETRIC_EDGE_TYPES = ("composes_with", "similar_to", "conflicts_with")

#: Relationships the planner is allowed to traverse when expanding a path.
#: ``conflicts_with`` is deliberately excluded: it is a "do not co-select"
#: signal, not a navigable relation, so walking it would pull in skills the plan
#: is meant to keep apart.
GRAPH_WALKABLE_EDGE_TYPES = ("depends_on", "specializes", "composes_with", "similar_to")

#: The only product name permitted in user-facing NexSkill surfaces.
PRODUCT_NAME = "NexSkill"

# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class NexSkillError(Exception):
    """Domain error carrying a stable error code and plain-language message.

    ``details`` is optional and must never include secrets, raw transcripts,
    provider names, or source names. The CLI maps every ``NexSkillError`` to
    the standard JSON error envelope.
    """

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details) if details else {}

    def to_error_dict(self) -> dict[str, Any]:
        """Error payload for the JSON envelope (no ``ok``/``op`` wrapper)."""
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _assert_code(code: str) -> None:
    if not isinstance(code, str) or not _CODE_RE.match(code):
        raise ValueError(f"error code must be UPPER_SNAKE, got {code!r}")


# ---------------------------------------------------------------------------
# JSON envelope
# ---------------------------------------------------------------------------


def success_envelope(op: str, result: dict[str, Any]) -> dict[str, Any]:
    """Standard success envelope: ``{ok, schema_version, op, result}``."""
    return {
        "ok": True,
        "schema_version": ENVELOPE_SCHEMA_VERSION,
        "op": op,
        "result": result,
    }


def error_envelope(op: str, error: NexSkillError) -> dict[str, Any]:
    """Standard error envelope: ``{ok:false, schema_version, op, error}``.

    The error ``code`` is validated to be stable ``UPPER_SNAKE`` so callers can
    branch on it without touching free text.
    """
    _assert_code(error.code)
    return {
        "ok": False,
        "schema_version": ENVELOPE_SCHEMA_VERSION,
        "op": op,
        "error": error.to_error_dict(),
    }


# ---------------------------------------------------------------------------
# Skill manifest
# ---------------------------------------------------------------------------

#: Required manifest fields (presence + non-empty validated).
SKILL_REQUIRED_FIELDS = ("schema_version", "id", "name", "summary", "stages", "entrypoint")

#: Entry types a skill may declare as ordering relationships with other skills.
SKILL_EDGE_TYPES = ("depends_on", "conflicts_with")

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


@dataclass(frozen=True)
class SkillManifest:
    """Validated view of a ``nexskill.skill.v1`` manifest.

    Validation is boundary-first: :func:`SkillManifest.from_dict` rejects
    malformed manifests with a stable ``SKILL_INVALID`` code so they never enter
    the registry. Unknown optional fields are preserved verbatim (forward
    compatibility) but not interpreted unless supported.
    """

    schema_version: str
    id: str
    name: str
    summary: str
    stages: list[str]
    entrypoint: str
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    conflicts_with: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    unknown: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SkillManifest":
        if not isinstance(raw, dict):
            raise NexSkillError("SKILL_INVALID", "manifest must be a JSON object")

        # schema_version
        sv = raw.get("schema_version")
        if sv != SKILL_SCHEMA_VERSION:
            raise NexSkillError(
                "SKILL_INVALID",
                f"manifest schema_version must be {SKILL_SCHEMA_VERSION}, got {sv!r}",
            )

        # required fields present and non-empty
        missing: list[str] = []
        for key in SKILL_REQUIRED_FIELDS:
            val = raw.get(key)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing.append(key)
        if missing:
            raise NexSkillError(
                "SKILL_INVALID",
                f"manifest missing required field(s): {', '.join(missing)}",
            )

        sid = raw["id"]
        if not _ID_RE.match(sid):
            raise NexSkillError(
                "SKILL_INVALID",
                "manifest id must be lowercase with dots, hyphens, or underscores "
                f"and start with an alphanumeric character; got {sid!r}",
            )

        stages = _as_str_list(raw, "stages", required=True)
        if not stages:
            raise NexSkillError("SKILL_INVALID", "manifest stages must be a non-empty list")

        known = set(SKILL_REQUIRED_FIELDS) | {"inputs", "outputs", "depends_on", "conflicts_with", "tags"}
        unknown = {k: v for k, v in raw.items() if k not in known}

        return cls(
            schema_version=sv,
            id=sid,
            name=raw["name"],
            summary=raw["summary"],
            stages=stages,
            entrypoint=raw["entrypoint"],
            inputs=_as_str_list(raw, "inputs"),
            outputs=_as_str_list(raw, "outputs"),
            depends_on=_as_str_list(raw, "depends_on"),
            conflicts_with=_as_str_list(raw, "conflicts_with"),
            tags=_as_str_list(raw, "tags"),
            unknown=unknown,
        )

    def to_index_dict(self) -> dict[str, Any]:
        """Compact metadata view for the registry index (no body, deterministic
        key order). Used by planners and ``skill list`` — never includes the
        skill body."""
        return {
            "id": self.id,
            "name": self.name,
            "summary": self.summary,
            "stages": list(self.stages),
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "depends_on": list(self.depends_on),
            "conflicts_with": list(self.conflicts_with),
            "tags": list(self.tags),
            "entrypoint": self.entrypoint,
        }


def _as_str_list(raw: dict[str, Any], key: str, *, required: bool = False) -> list[str]:
    val = raw.get(key, [])
    if val is None:
        val = []
    if not isinstance(val, list):
        raise NexSkillError("SKILL_INVALID", f"manifest {key} must be a list")
    out: list[str] = []
    for item in val:
        if not isinstance(item, str) or not item.strip():
            if required:
                raise NexSkillError("SKILL_INVALID", f"manifest {key} contains an empty entry")
            continue
        out.append(item.strip())
    return out


# ---------------------------------------------------------------------------
# Project config (.nexskill/config.json)
# ---------------------------------------------------------------------------

DEFAULT_SKILL_SOURCE_PATH = ".nexskill/skills"


@dataclass(frozen=True)
class SkillSource:
    """A configured local skill source."""

    type: str
    path: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SkillSource":
        if not isinstance(raw, dict):
            raise NexSkillError("CONFIG_INVALID", "skill_sources entry must be an object")
        stype = raw.get("type")
        if stype != "local":
            raise NexSkillError(
                "CONFIG_INVALID",
                f"skill source type must be 'local', got {stype!r}",
            )
        path = raw.get("path")
        if not isinstance(path, str) or not path.strip():
            raise NexSkillError("CONFIG_INVALID", "skill source path is required")
        return cls(type=stype, path=path.strip())


@dataclass(frozen=True)
class CheckConfig:
    """A configured proof check."""

    id: str
    command: str
    required: bool = True

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CheckConfig":
        if not isinstance(raw, dict):
            raise NexSkillError("CONFIG_INVALID", "checks entry must be an object")
        cid = raw.get("id")
        if not isinstance(cid, str) or not cid.strip():
            raise NexSkillError("CONFIG_INVALID", "check id is required")
        command = raw.get("command")
        if not isinstance(command, str) or not command.strip():
            raise NexSkillError("CONFIG_INVALID", f"check '{cid}' command is required")
        required = raw.get("required", True)
        if not isinstance(required, bool):
            raise NexSkillError("CONFIG_INVALID", f"check '{cid}' required must be a boolean")
        return cls(id=cid.strip(), command=command.strip(), required=required)


@dataclass
class ProjectConfig:
    """Validated ``.nexskill/config.json``.

    Boundary validation lives in :func:`ProjectConfig.from_dict`. Optional
    sections default to safe, dependency-light values so a freshly initialised
    project still works without external tools.
    """

    schema_version: str
    project_name: str
    skill_sources: list[SkillSource]
    checks: list[CheckConfig]
    policies: dict[str, Any]
    default_checks: list[str] = field(default_factory=list)
    unknown: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ProjectConfig":
        if not isinstance(raw, dict):
            raise NexSkillError("CONFIG_INVALID", "config must be a JSON object")
        sv = raw.get("schema_version")
        if sv != CONFIG_SCHEMA_VERSION:
            raise NexSkillError(
                "CONFIG_INVALID",
                f"config schema_version must be {CONFIG_SCHEMA_VERSION}, got {sv!r}",
            )

        project_name = raw.get("project_name")
        if not isinstance(project_name, str) or not project_name.strip():
            raise NexSkillError("CONFIG_INVALID", "project_name is required")

        src_raw = raw.get("skill_sources", [])
        if not isinstance(src_raw, list):
            raise NexSkillError("CONFIG_INVALID", "skill_sources must be a list")
        skill_sources = [SkillSource.from_dict(s) for s in src_raw]

        checks_raw = raw.get("checks", [])
        if not isinstance(checks_raw, list):
            raise NexSkillError("CONFIG_INVALID", "checks must be a list")
        checks = [CheckConfig.from_dict(c) for c in checks_raw]

        policies = raw.get("policies", {})
        if not isinstance(policies, dict):
            raise NexSkillError("CONFIG_INVALID", "policies must be an object")

        dc_raw = raw.get("default_checks", [])
        if not isinstance(dc_raw, list):
            raise NexSkillError("CONFIG_INVALID", "default_checks must be a list")
        default_checks = [c.strip() for c in dc_raw if isinstance(c, str) and c.strip()]

        known_top = {
            "schema_version", "project_name", "skill_sources", "checks",
            "policies", "default_checks",
        }
        unknown = {k: v for k, v in raw.items() if k not in known_top}

        return cls(
            schema_version=sv,
            project_name=project_name.strip(),
            skill_sources=skill_sources,
            checks=checks,
            policies=dict(policies),
            default_checks=default_checks,
            unknown=unknown,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise back to a deterministic config dict for ``init``."""
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "skill_sources": [{"type": s.type, "path": s.path} for s in self.skill_sources],
            "checks": [
                {"id": c.id, "command": c.command, "required": c.required} for c in self.checks
            ],
            "default_checks": list(self.default_checks),
            "policies": dict(self.policies),
        }


#: Portable, dependency-light built-in checks enabled by ``nexskill init``.
#: Every one of these is safe on any repository: it needs no external tools
#: beyond optional git, never fails the build (failures surface as warnings),
#: and degrades to ``skipped`` when its precondition is absent. See
#: ``nexskill.proof`` for the implementations.
DEFAULT_BUILTIN_CHECKS = ("skills-valid", "report-hygiene", "git-clean")


def default_config(project_name: str) -> ProjectConfig:
    """A safe starter config for ``nexskill init``.

    It declares the standard local skill source, no required external-command
    checks, a portable built-in default-check set, and the default NexSkill
    policies. The built-in checks are advisory and dependency-light, so a fresh
    project gets a meaningful ``check`` out of the box while still working
    without any external tools.
    """
    return ProjectConfig(
        schema_version=CONFIG_SCHEMA_VERSION,
        project_name=project_name,
        skill_sources=[SkillSource(type="local", path=DEFAULT_SKILL_SOURCE_PATH)],
        checks=[],
        default_checks=list(DEFAULT_BUILTIN_CHECKS),
        policies={
            "product_name": PRODUCT_NAME,
            "forbid_source_names_in_reports": True,
        },
    )


# ---------------------------------------------------------------------------
# Evidence (.nexskill/evidence.jsonl)
# ---------------------------------------------------------------------------

#: Allowed ``op`` values for an evidence event.
EVIDENCE_OPS = ("init", "plan", "check", "closeout")
EVIDENCE_STATUSES = ("passed", "failed", "warning", "skipped")


@dataclass(frozen=True)
class EvidenceEvent:
    """One append-only local evidence event."""

    schema_version: str
    event_id: str
    op: str
    status: str
    timestamp: str
    summary: str
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EvidenceEvent":
        if not isinstance(raw, dict):
            raise NexSkillError("EVIDENCE_INVALID", "evidence event must be a JSON object")
        sv = raw.get("schema_version")
        if sv != EVIDENCE_SCHEMA_VERSION:
            raise NexSkillError(
                "EVIDENCE_INVALID",
                f"evidence schema_version must be {EVIDENCE_SCHEMA_VERSION}, got {sv!r}",
            )
        for key in ("event_id", "op", "status", "timestamp", "summary"):
            val = raw.get(key)
            if not isinstance(val, str) or not val.strip():
                raise NexSkillError("EVIDENCE_INVALID", f"evidence {key} is required")
        op = raw["op"]
        if op not in EVIDENCE_OPS:
            raise NexSkillError("EVIDENCE_INVALID", f"evidence op must be one of {EVIDENCE_OPS}, got {op!r}")
        status = raw["status"]
        if status not in EVIDENCE_STATUSES:
            raise NexSkillError(
                "EVIDENCE_INVALID",
                f"evidence status must be one of {EVIDENCE_STATUSES}, got {status!r}",
            )
        data = raw.get("data", {})
        if not isinstance(data, dict):
            raise NexSkillError("EVIDENCE_INVALID", "evidence data must be an object")
        return cls(
            schema_version=sv,
            event_id=raw["event_id"],
            op=op,
            status=status,
            timestamp=raw["timestamp"],
            summary=raw["summary"],
            data=dict(data),
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
# Plan / check result shapes (shared by planner, proof runner, reports)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlanStep:
    """One step in a bounded skill path."""

    skill_id: str
    name: str
    summary: str
    stage: str
    reason: str


@dataclass(frozen=True)
class PlanResult:
    """Bounded, ordered skill path for a task."""

    task: str
    stages: list[str]
    steps: list[PlanStep]
    conflicts: list[dict[str, str]]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "stages": list(self.stages),
            "steps": [
                {
                    "skill_id": s.skill_id,
                    "name": s.name,
                    "summary": s.summary,
                    "stage": s.stage,
                    "reason": s.reason,
                }
                for s in self.steps
            ],
            "conflicts": [dict(c) for c in self.conflicts],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class CheckOutcome:
    """One configured check outcome."""

    id: str
    command: str
    required: bool
    status: str  # passed | failed | skipped | warning
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "command": self.command,
            "required": self.required,
            "status": self.status,
            "message": self.message,
        }

    def to_safe_dict(self) -> dict[str, Any]:
        """Evidence/report-safe view: drops the raw command string, which is
        owner-configured and may embed secrets when persisted. Callers that
        record evidence or build reports should use this view."""
        return {
            "id": self.id,
            "required": self.required,
            "status": self.status,
            "message": self.message,
        }


@dataclass(frozen=True)
class CheckResult:
    """Aggregate result of a proof run (check or closeout)."""

    op: str  # check | closeout
    status: str  # passed | failed | warning
    checks: list[CheckOutcome]
    blockers: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "op": self.op,
            "status": self.status,
            "checks": [c.to_dict() for c in self.checks],
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }
