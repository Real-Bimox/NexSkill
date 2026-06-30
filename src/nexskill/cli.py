"""NexSkill command-line interface.

Public command family:

    nexskill init   [--repo <path>] [--force]
    nexskill plan   "<task>" [--repo <path>] [--json]
    nexskill check  [--repo <path>] [--json]
    nexskill closeout [--repo <path>] [--json]
    nexskill skill  list|validate|scaffold ... [--repo <path>] [--json]

Every ``--json`` command emits one envelope:

    {"ok": true, "schema_version": "nexskill.v1", "op": "...", "result": {...}}

Errors use the same envelope with ``ok: false`` and a stable error code. Human
output is concise and uses only the NexSkill product name.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

from . import proof, report, scaffold
from .contracts import (
    NexSkillError,
    PRODUCT_NAME,
    default_config,
    error_envelope,
    success_envelope,
)
from .planner import GraphPlanner
from .registry import SkillRegistry

# Seed skill corpus shipped with the package, copied into .nexskill/skills on
# init so a fresh project has useful skills out of the box.
SEED_SKILLS_DIR = Path(__file__).resolve().parents[2] / "data" / "nexskill_skills"


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _emit_json(payload: dict[str, Any], exit_code: int = 0) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    raise _Exit(exit_code)


class _Exit(Exception):
    def __init__(self, code: int):
        self.code = code


def _human(msg: str) -> None:
    sys.stdout.write(msg + "\n")


def _err(msg: str) -> None:
    sys.stderr.write(msg + "\n")


# ---------------------------------------------------------------------------
# Command: init
# ---------------------------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    force = bool(args.force)
    project_name = args.project_name or repo.name or "project"

    cfg_path = proof.config_path(repo)
    if cfg_path.exists() and not force:
        raise NexSkillError(
            "CONFIG_EXISTS",
            f"{cfg_path} already exists. Use --force to overwrite.",
        )

    config = default_config(project_name)
    proof.write_config(repo, config)

    # Seed the local skills directory from the shipped corpus so planning works
    # immediately. Existing skill packages are preserved (not overwritten).
    skills_dir = repo / ".nexskill" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    seeded: list[str] = []
    if SEED_SKILLS_DIR.exists():
        for pkg in sorted(SEED_SKILLS_DIR.iterdir()):
            if not pkg.is_dir():
                continue
            dest = skills_dir / pkg.name
            if dest.exists():
                continue
            shutil.copytree(pkg, dest)
            seeded.append(pkg.name)

    proof.record_init(repo, project_name)

    result = {
        "config": str(cfg_path.relative_to(repo)) if cfg_path.is_relative_to(repo) else str(cfg_path),
        "project_name": project_name,
        "skills_seeded": seeded,
        "skills_dir": ".nexskill/skills",
    }
    if not args.json:
        _human(f"{PRODUCT_NAME} initialized project '{project_name}'.")
        _human(f"  config: {result['config']}")
        if seeded:
            _human(f"  seeded {len(seeded)} skill package(s) into .nexskill/skills")
        _human("Next: nexskill plan \"<task>\"")
    return _finish(success_envelope("init", result), args.json, exit_code=0)


# ---------------------------------------------------------------------------
# Command: plan
# ---------------------------------------------------------------------------


def _load_registry(repo: Path):
    config = proof.load_config(repo)
    registry, reg_report = SkillRegistry.load(config.skill_sources, repo)
    return config, registry, reg_report


def cmd_plan(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    config, registry, reg_report = _load_registry(repo)

    planner = GraphPlanner(registry)
    plan_result = planner.plan(args.task)
    proof.record_plan(repo, plan_result.to_dict())

    # Write an advisory report so the owner can see the plan.
    rep = report.build_report(
        task=args.task, plan=plan_result, check=None,
        project_name=config.project_name, repo_root=repo,
    )
    report.write_report(repo, rep)

    result = {
        "task": plan_result.task,
        "stages": plan_result.stages,
        "steps": [s.__dict__ if hasattr(s, "__dict__") else s for s in []] or _plan_steps(plan_result),
        "conflicts": plan_result.conflicts,
        "warnings": plan_result.warnings,
        "registry": {"loaded": len(registry), "skipped": len(reg_report.skipped)},
        "report": ".nexskill/reports/latest.json",
    }
    if not args.json:
        _human(f"{PRODUCT_NAME} planned a skill path for: {args.task}")
        _human(f"  stages: {' → '.join(plan_result.stages) if plan_result.stages else '(none)'}")
        for i, step in enumerate(plan_result.steps, start=1):
            _human(f"  {i}. {step.name} [{step.stage}]")
            if step.summary:
                _human(f"     {step.summary}")
        for w in plan_result.warnings:
            _human(f"  ! {w}")
        _human("Next: nexskill check --repo .")
    return _finish(success_envelope("plan", result), args.json, exit_code=0)


def _plan_steps(plan_result) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for s in plan_result.steps:
        out.append(
            {
                "skill_id": s.skill_id,
                "name": s.name,
                "summary": s.summary,
                "stage": s.stage,
                "reason": s.reason,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Command: check
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    config = proof.load_config(repo)
    result = proof.run_checks(repo, config=config)

    # Optional advisory report (no plan context here).
    rep = report.build_report(
        task=None, plan=None, check=result,
        project_name=config.project_name, repo_root=repo,
    )
    report.write_report(repo, rep)

    payload = success_envelope("check", result.to_dict())
    exit_code = 0 if result.status != "failed" else 1
    if not args.json:
        _human(f"{PRODUCT_NAME} check: {result.status}")
        for c in result.checks:
            mark = {"passed": "OK", "failed": "FAIL", "warning": "WARN", "skipped": "SKIP"}.get(c.status, "?")
            _human(f"  [{mark}] {c.id}: {c.message}")
        for b in result.blockers:
            _human(f"  blocker: {b}")
        for w in result.warnings:
            _human(f"  warning: {w}")
    return _finish(payload, args.json, exit_code=exit_code)


# ---------------------------------------------------------------------------
# Command: closeout
# ---------------------------------------------------------------------------


def cmd_closeout(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    config = proof.load_config(repo)
    result = proof.closeout(repo, config=config)

    rep = report.build_report(
        task=None, plan=None, check=result,
        project_name=config.project_name, repo_root=repo,
    )
    report.write_report(repo, rep)

    payload = success_envelope("closeout", result.to_dict())
    exit_code = 0 if result.status != "failed" else 1
    if not args.json:
        _human(f"{PRODUCT_NAME} closeout: {result.status}")
        _human(f"  evidence: .nexskill/evidence.jsonl")
        _human(f"  report:   .nexskill/reports/latest.md")
        for b in result.blockers:
            _human(f"  blocker: {b}")
    return _finish(payload, args.json, exit_code=exit_code)


# ---------------------------------------------------------------------------
# Command: skill (list / validate)
# ---------------------------------------------------------------------------


def cmd_skill_list(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    _config, registry, reg_report = _load_registry(repo)
    payload = success_envelope(
        "skill-list",
        {"skills": registry.index(), "loaded": len(registry), "skipped": reg_report.skipped},
    )
    if not args.json:
        skills = registry.all()
        _human(f"{PRODUCT_NAME} skills: {len(skills)} loaded")
        for s in skills:
            _human(f"  - {s.id} [{', '.join(s.manifest.stages)}]: {s.manifest.name}")
        for skip in reg_report.skipped:
            _human(f"  ! skipped {skip['package']}: {skip['code']}")
    return _finish(payload, args.json, exit_code=0)


def cmd_skill_validate(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    _config, _registry, reg_report = _load_registry(repo)
    payload = success_envelope(
        "skill-validate", {"valid": reg_report.ok, "skipped": reg_report.skipped}
    )
    exit_code = 0 if reg_report.ok else 1
    if not args.json:
        status = "valid" if reg_report.ok else "has issues"
        _human(f"{PRODUCT_NAME} skill validate: {status}")
        for skip in reg_report.skipped:
            _human(f"  ! {skip['package']}: {skip['code']} - {skip['reason']}")
    return _finish(payload, args.json, exit_code=exit_code)


# ---------------------------------------------------------------------------
# Command: skill scaffold
# ---------------------------------------------------------------------------


def cmd_skill_scaffold(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    result = scaffold.scaffold_skill(
        args.name,
        repo,
        id=args.id,
        name=args.display_name,
        summary=args.summary,
        stage=args.stage,
        force=bool(args.force),
    )
    payload = success_envelope(
        "skill-scaffold",
        result.to_dict(repo_root=repo),
    )
    if not args.json:
        rel = payload["result"]["package_dir"]
        _human(f"{PRODUCT_NAME} scaffolded skill '{result.skill_id}'.")
        _human(f"  package: {rel}")
        _human(f"  files:   {', '.join(result.files_written)}")
        _human("Next: nexskill skill validate --repo .")
    return _finish(payload, args.json, exit_code=0)


# ---------------------------------------------------------------------------
# Finish + dispatch
# ---------------------------------------------------------------------------


def _finish(payload: dict[str, Any], json_mode: bool, exit_code: int) -> int:
    if json_mode:
        _emit_json(payload, exit_code=exit_code)
    return exit_code


def _run_command(func: Callable[[argparse.Namespace], int], args: argparse.Namespace) -> int:
    op = getattr(args, "_op", "nexskill")
    try:
        return func(args)
    except NexSkillError as exc:
        if getattr(args, "json", False):
            _emit_json(error_envelope(op, exc), exit_code=1)
        _err(f"{PRODUCT_NAME} error [{exc.code}]: {exc.message}")
        return 1
    except _Exit as e:
        return e.code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nexskill",
        description=f"{PRODUCT_NAME} guides the work, selects the right skill path, and proves the result.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p = sub.add_parser("init", help="Initialize NexSkill config in a repository.")
    p.add_argument("--repo", default=".", help="Repository path (default: current directory).")
    p.add_argument("--force", action="store_true", help="Overwrite an existing config.")
    p.add_argument("--project-name", default=None, help="Project name for the config.")
    p.add_argument("--json", action="store_true", help="Emit JSON envelope.")
    p.set_defaults(func=cmd_init, _op="init")

    # plan
    p = sub.add_parser("plan", help="Plan a bounded skill path for a task.")
    p.add_argument("task", help="Task description to plan for.")
    p.add_argument("--repo", default=".", help="Repository path.")
    p.add_argument("--json", action="store_true", help="Emit JSON envelope.")
    p.set_defaults(func=cmd_plan, _op="plan")

    # check
    p = sub.add_parser("check", help="Run configured local proof checks.")
    p.add_argument("--repo", default=".", help="Repository path.")
    p.add_argument("--json", action="store_true", help="Emit JSON envelope.")
    p.set_defaults(func=cmd_check, _op="check")

    # closeout
    p = sub.add_parser("closeout", help="Run checks and record closeout evidence.")
    p.add_argument("--repo", default=".", help="Repository path.")
    p.add_argument("--json", action="store_true", help="Emit JSON envelope.")
    p.set_defaults(func=cmd_closeout, _op="closeout")

    # skill
    p_skill = sub.add_parser("skill", help="Inspect or validate skill packages.")
    skill_sub = p_skill.add_subparsers(dest="skill_command", required=True)

    p_sl = skill_sub.add_parser("list", help="List discovered skill packages.")
    p_sl.add_argument("--repo", default=".", help="Repository path.")
    p_sl.add_argument("--json", action="store_true", help="Emit JSON envelope.")
    p_sl.set_defaults(func=cmd_skill_list, _op="skill-list")

    p_sv = skill_sub.add_parser("validate", help="Validate all skill package manifests.")
    p_sv.add_argument("--repo", default=".", help="Repository path.")
    p_sv.add_argument("--json", action="store_true", help="Emit JSON envelope.")
    p_sv.set_defaults(func=cmd_skill_validate, _op="skill-validate")

    p_sc = skill_sub.add_parser(
        "scaffold", help="Scaffold a new skill package from the shipped template."
    )
    p_sc.add_argument("name", help="Skill package name (e.g. reviewing.checklist).")
    p_sc.add_argument("--id", default=None, help="Override the skill id (defaults to <name>).")
    p_sc.add_argument("--name", dest="display_name", default=None, help="Human-readable skill name.")
    p_sc.add_argument("--summary", default=None, help="One-line skill summary.")
    p_sc.add_argument("--stage", default=None, help="Development stage (default: building).")
    p_sc.add_argument("--force", action="store_true", help="Overwrite an existing package.")
    p_sc.add_argument("--repo", default=".", help="Repository path.")
    p_sc.add_argument("--json", action="store_true", help="Emit JSON envelope.")
    p_sc.set_defaults(func=cmd_skill_scaffold, _op="skill-scaffold")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return _run_command(args.func, args)


if __name__ == "__main__":
    raise SystemExit(main())
