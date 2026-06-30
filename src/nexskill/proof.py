"""NexSkill proof runner.

Runs configured local checks and records evidence. The proof engine proves
local claims wherever practical; it never auto-repairs failures and never grants
merge or release authority. A failed required check is a blocker; a failed
optional check is a warning only.

Evidence is written as append-only JSONL at ``.nexskill/evidence.jsonl``. Each
event is one JSON object per line. The summary field is plain language and must
never include secrets, raw transcripts, or source/provider names.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import (
    CONFIG_SCHEMA_VERSION,
    EVIDENCE_SCHEMA_VERSION,
    CheckConfig,
    CheckOutcome,
    CheckResult,
    EvidenceEvent,
    NexSkillError,
    ProjectConfig,
)

CONFIG_FILENAME = "config.json"
NEXSKILL_DIR = ".nexskill"
EVIDENCE_FILENAME = "evidence.jsonl"
REPORTS_DIRNAME = "reports"

#: Commands that run shell commands are a privilege. We execute the configured
#: command verbatim because the config is owner-controlled, but we keep the
#: surface minimal: no shell injection from the task text, short timeouts.
CHECK_TIMEOUT_S = 120

#: Patterns that look like secrets. Defence-in-depth: command output is
#: owner-environment-dependent and may print credentials, so we redact these
#: from any message that is persisted into evidence or reports. This is a
#: best-effort scrub, not a guarantee — owners should still avoid printing
#: secrets from check commands.
_SECRET_PATTERNS = [
    # KEY=VALUE style (API_KEY=..., SECRET=..., TOKEN=...)
    (re.compile(r"(?i)(\b[A-Z0-9_]{2,}(?:KEY|SECRET|TOKEN|PASSWORD|PASS|CRED)[A-Z0-9_]*\s*=\s*)(\S+)"), r"\1***"),
    # Bearer / token headers
    (re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._\-]{8,})"), r"\1***"),
    # Long hex / base64 blobs (32+ chars) that commonly are keys/tokens
    (re.compile(r"\b([A-Za-z0-9+/=_\-]{32,})\b"), "***"),
]


def _redact(text: str) -> str:
    """Best-effort redaction of secret-like substrings from command output."""
    if not text:
        return text
    out = text
    for pattern, repl in _SECRET_PATTERNS:
        out = pattern.sub(repl, out)
    return out


def utc_now_iso() -> str:
    """Stable UTC timestamp in ISO-8601 with a trailing ``Z``."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_event_id() -> str:
    """Locally-unique event id (timestamp + random suffix)."""
    return f"evt-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def nexskill_dir(repo_root: Path) -> Path:
    return repo_root / NEXSKILL_DIR


def config_path(repo_root: Path) -> Path:
    return nexskill_dir(repo_root) / CONFIG_FILENAME


def evidence_path(repo_root: Path) -> Path:
    return nexskill_dir(repo_root) / EVIDENCE_FILENAME


def reports_dir(repo_root: Path) -> Path:
    return nexskill_dir(repo_root) / REPORTS_DIRNAME


def config_exists(repo_root: Path) -> bool:
    return config_path(repo_root).exists()


# ---------------------------------------------------------------------------
# Config load / init
# ---------------------------------------------------------------------------


def load_config(repo_root: Path) -> ProjectConfig:
    """Load and validate ``.nexskill/config.json``. Raises a stable error if the
    config is missing or invalid."""
    path = config_path(repo_root)
    if not path.exists():
        raise NexSkillError(
            "CONFIG_MISSING",
            "NexSkill is not initialized in this repository. Run `nexskill init` first.",
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise NexSkillError("CONFIG_INVALID", f"config.json is not valid JSON: {exc.msg}") from exc
    return ProjectConfig.from_dict(raw)


def write_config(repo_root: Path, config: ProjectConfig) -> Path:
    """Atomically write a config (used by ``nexskill init``)."""
    path = config_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(
        json.dumps(config.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)
    return path


# ---------------------------------------------------------------------------
# Evidence writer
# ---------------------------------------------------------------------------


def append_evidence(repo_root: Path, event: EvidenceEvent) -> Path:
    """Append one evidence event as a JSONL line. Creates the directory if
    needed. The file is append-only across runs."""
    path = evidence_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return path


def read_evidence(repo_root: Path) -> list[EvidenceEvent]:
    """Read and validate every line of the evidence file."""
    path = evidence_path(repo_root)
    if not path.exists():
        return []
    events: list[EvidenceEvent] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise NexSkillError(
                "EVIDENCE_INVALID", f"evidence.jsonl line {lineno} is not valid JSON: {exc.msg}"
            ) from exc
        events.append(EvidenceEvent.from_dict(raw))
    return events


# ---------------------------------------------------------------------------
# Check execution
# ---------------------------------------------------------------------------


def _run_command(command: str, repo_root: Path) -> tuple[bool, str]:
    """Run a configured check command. Returns (passed, message).

    The command is owner-controlled and run verbatim. We pass a bounded timeout
    and capture stdout/stderr truncated to keep evidence small and secret-free.
    """
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=CHECK_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {CHECK_TIMEOUT_S}s."
    except FileNotFoundError as exc:
        return False, f"Command not found: {exc.filename or command}"
    if proc.returncode == 0:
        return True, "Command succeeded."
    snippet = (proc.stderr or proc.stdout or "").strip().splitlines()
    tail = snippet[-1] if snippet else f"exit code {proc.returncode}"
    return False, f"Command failed ({_redact(tail)[:160]})"


def _outcome_for(check: CheckConfig, repo_root: Path) -> CheckOutcome:
    passed, message = _run_command(check.command, repo_root)
    if passed:
        return CheckOutcome(
            id=check.id, command=check.command, required=check.required,
            status="passed", message=message,
        )
    status = "failed" if check.required else "warning"
    return CheckOutcome(
        id=check.id, command=check.command, required=check.required,
        status=status, message=message,
    )


def _config_integrity_check(repo_root: Path) -> CheckOutcome:
    """Always-on check: NexSkill config must be present and valid."""
    try:
        load_config(repo_root)
    except NexSkillError as exc:
        return CheckOutcome(
            id="config", command="(internal)", required=True,
            status="failed", message=f"{exc.code}: {exc.message}",
        )
    return CheckOutcome(
        id="config", command="(internal)", required=True,
        status="passed", message="Config present and valid.",
    )


# ---------------------------------------------------------------------------
# Portable built-in checks
# ---------------------------------------------------------------------------
#
# These run with no owner configuration and no external tooling beyond optional
# git. They are advisory by design (``required=False``): the worst outcome is a
# warning, never a blocker, and any check whose precondition is absent reports
# ``skipped``. That keeps a fresh project's ``check`` meaningful without ever
# turning a portable default into a build gate.


def _builtin_skills_valid(repo_root: Path, config: ProjectConfig) -> CheckOutcome:
    """Every discovered skill manifest is valid (none skipped)."""
    from .registry import SkillRegistry

    _registry, report = SkillRegistry.load(config.skill_sources, repo_root)
    if report.skipped:
        return CheckOutcome(
            id="skills-valid", command="(internal)", required=False,
            status="warning",
            message=f"{len(report.skipped)} skill manifest(s) failed validation.",
        )
    return CheckOutcome(
        id="skills-valid", command="(internal)", required=False,
        status="passed",
        message=f"{len(report.loaded)} skill manifest(s) valid.",
    )


def _builtin_report_hygiene(repo_root: Path, config: ProjectConfig) -> CheckOutcome:
    """Generated reports and evidence carry no forbidden source/provider names."""
    from .report import FORBIDDEN_SOURCE_NAMES

    targets = [
        reports_dir(repo_root) / "latest.json",
        reports_dir(repo_root) / "latest.md",
        evidence_path(repo_root),
    ]
    blob = ""
    for path in targets:
        if path.exists():
            blob += path.read_text(encoding="utf-8", errors="ignore").lower()
    if not blob:
        return CheckOutcome(
            id="report-hygiene", command="(internal)", required=False,
            status="skipped", message="No generated reports or evidence yet.",
        )
    found = sorted({name for name in FORBIDDEN_SOURCE_NAMES if name.lower() in blob})
    if found:
        return CheckOutcome(
            id="report-hygiene", command="(internal)", required=False,
            status="warning",
            message=f"{len(found)} forbidden source name(s) found in generated output.",
        )
    return CheckOutcome(
        id="report-hygiene", command="(internal)", required=False,
        status="passed", message="Generated output is free of forbidden source names.",
    )


def _builtin_git_clean(repo_root: Path, config: ProjectConfig) -> CheckOutcome:
    """The working tree has no uncommitted changes (advisory)."""
    if not (repo_root / ".git").exists():
        return CheckOutcome(
            id="git-clean", command="(internal)", required=False,
            status="skipped", message="Not a git repository; skipped.",
        )
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_root), capture_output=True, text=True, timeout=CHECK_TIMEOUT_S,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return CheckOutcome(
            id="git-clean", command="(internal)", required=False,
            status="skipped", message="git unavailable; skipped.",
        )
    if proc.returncode != 0:
        return CheckOutcome(
            id="git-clean", command="(internal)", required=False,
            status="skipped", message="git status unavailable; skipped.",
        )
    dirty = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    if dirty:
        return CheckOutcome(
            id="git-clean", command="(internal)", required=False,
            status="warning", message=f"Working tree has {len(dirty)} uncommitted change(s).",
        )
    return CheckOutcome(
        id="git-clean", command="(internal)", required=False,
        status="passed", message="Working tree is clean.",
    )


#: Built-in check id -> implementation. Enabled per project via
#: ``config.default_checks``. Adding a project's own command checks still goes
#: through ``config.checks`` and needs no code here.
BUILTIN_CHECKS = {
    "skills-valid": _builtin_skills_valid,
    "report-hygiene": _builtin_report_hygiene,
    "git-clean": _builtin_git_clean,
}


def _builtin_outcome(check_id: str, repo_root: Path, config: ProjectConfig) -> CheckOutcome:
    impl = BUILTIN_CHECKS.get(check_id)
    if impl is None:
        return CheckOutcome(
            id=check_id, command="(internal)", required=False,
            status="skipped", message="Unknown built-in check; skipped.",
        )
    return impl(repo_root, config)


def run_checks(repo_root: Path, *, config: ProjectConfig | None = None) -> CheckResult:
    """Run the always-on config check plus every configured command check.

    Required-check failures become blockers and set the aggregate status to
    ``failed``; optional failures become warnings only. This function does not
    write evidence — :func:`closeout` does, so check and closeout can share the
    same execution core while closeout additionally records.
    """
    if config is None:
        config = load_config(repo_root)

    outcomes: list[CheckOutcome] = [_config_integrity_check(repo_root)]
    for check_id in config.default_checks:
        outcomes.append(_builtin_outcome(check_id, repo_root, config))
    for check in config.checks:
        outcomes.append(_outcome_for(check, repo_root))

    blockers = [f"{o.id}: {o.message}" for o in outcomes if o.status == "failed"]
    warnings = [f"{o.id}: {o.message}" for o in outcomes if o.status == "warning"]

    if blockers:
        status = "failed"
    elif warnings:
        status = "warning"
    else:
        status = "passed"

    return CheckResult(op="check", status=status, checks=outcomes, blockers=blockers, warnings=warnings)


def closeout(
    repo_root: Path,
    *,
    config: ProjectConfig | None = None,
    duration_ms: int | None = None,
) -> CheckResult:
    """Run checks and record evidence of the outcome.

    Evidence is recorded even on failure (failures are evidence, not hidden).
    The closeout result is the same shape as a check result but with
    ``op='closeout'`` and includes the recorded evidence path. When
    ``duration_ms`` is supplied it is recorded as latency evidence.
    """
    if config is None:
        config = load_config(repo_root)
    result = run_checks(repo_root, config=config)

    status = result.status if result.status in ("passed", "failed", "warning") else "warning"
    summary = (
        "All required checks passed."
        if status == "passed"
        else ("Required checks failed." if status == "failed" else "Checks passed with warnings.")
    )
    data: dict[str, Any] = {
        "checks": [o.to_safe_dict() for o in result.checks],
        "blockers": result.blockers,
        "warnings": result.warnings,
    }
    if duration_ms is not None:
        data["duration_ms"] = int(duration_ms)
    event = EvidenceEvent(
        schema_version=EVIDENCE_SCHEMA_VERSION,
        event_id=new_event_id(),
        op="closeout",
        status=status,
        timestamp=utc_now_iso(),
        summary=summary,
        data=data,
    )
    append_evidence(repo_root, event)

    # Re-shape as a closeout result carrying the evidence record.
    return CheckResult(
        op="closeout",
        status=result.status,
        checks=result.checks,
        blockers=result.blockers,
        warnings=result.warnings + [f"Evidence recorded: {evidence_path(repo_root).name}"],
    )


# ---------------------------------------------------------------------------
# Init evidence (recorded by nexskill init)
# ---------------------------------------------------------------------------


def record_init(repo_root: Path, project_name: str) -> Path:
    event = EvidenceEvent(
        schema_version=EVIDENCE_SCHEMA_VERSION,
        event_id=new_event_id(),
        op="init",
        status="passed",
        timestamp=utc_now_iso(),
        summary=f"NexSkill initialized for project '{project_name}'.",
        data={"project_name": project_name, "schema_version": CONFIG_SCHEMA_VERSION},
    )
    return append_evidence(repo_root, event)


def record_plan(
    repo_root: Path,
    plan_dict: dict[str, Any],
    duration_ms: int | None = None,
) -> Path:
    """Record a lightweight advisory evidence event for a plan (derived, not
    trusted-local). When ``duration_ms`` is supplied it is recorded as latency
    evidence."""
    n = len(plan_dict.get("steps", []))
    data: dict[str, Any] = {"steps": n, "stages": plan_dict.get("stages", [])}
    if duration_ms is not None:
        data["duration_ms"] = int(duration_ms)
    event = EvidenceEvent(
        schema_version=EVIDENCE_SCHEMA_VERSION,
        event_id=new_event_id(),
        op="plan",
        status="passed",
        timestamp=utc_now_iso(),
        summary=f"Plan produced {n} skill step(s). Advisory.",
        data=data,
    )
    return append_evidence(repo_root, event)
