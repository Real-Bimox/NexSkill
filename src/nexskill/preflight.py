"""NexSkill lane isolation preflight.

A small, deterministic, standard-library-only check an agent runs *before*
starting NexSkill work to confirm it is in the right place and not about to
collide with another lane.

It inspects git/worktree state only — it never reads ``.nexskill/config.json``,
makes a network call, or mutates the repository — so it is safe to run at any
time. It reports:

- the current worktree path, branch, and HEAD commit;
- the upstream branch, if any;
- dirty tracked files and untracked files;
- whether the current branch matches the expected branch;
- whether the expected base ref is an ancestor of HEAD.

It fails (non-zero exit, ``ok: false``) when the current branch is not the
expected one, the worktree has tracked changes, unexpected untracked files
exist, or the branch is missing its expected base. Untracked paths a lane
legitimately carries (for example another lane's files that are merely present
on disk) can be allow-listed so they do not trip the check.

Run it directly::

    python -m nexskill.preflight --expected-branch <name> --expected-base <ref>

or through the product command family::

    nexskill preflight --expected-branch <name> --expected-base <ref> [--json]
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any

from .contracts import ENVELOPE_SCHEMA_VERSION, PRODUCT_NAME


@dataclass(frozen=True)
class Failure:
    """One preflight failure with a stable code and plain-language message."""

    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass
class PreflightResult:
    """The gathered lane state plus the verdict."""

    worktree: str | None
    branch: str | None
    head: str | None
    upstream: str | None
    expected_branch: str | None
    expected_base: str | None
    branch_matches: bool
    base_is_ancestor: bool
    dirty_tracked: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    unexpected_untracked: list[str] = field(default_factory=list)
    failures: list[Failure] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    @property
    def summary(self) -> str:
        if self.ok:
            return "Lane is isolated and ready."
        return f"{len(self.failures)} preflight check(s) failed."

    def to_result_dict(self) -> dict[str, Any]:
        return {
            "worktree": self.worktree,
            "branch": self.branch,
            "head": self.head,
            "upstream": self.upstream,
            "expected_branch": self.expected_branch,
            "expected_base": self.expected_base,
            "branch_matches": self.branch_matches,
            "base_is_ancestor": self.base_is_ancestor,
            "dirty_tracked": list(self.dirty_tracked),
            "untracked": list(self.untracked),
            "unexpected_untracked": list(self.unexpected_untracked),
            "failures": [f.to_dict() for f in self.failures],
            "summary": self.summary,
        }

    def to_envelope(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "schema_version": ENVELOPE_SCHEMA_VERSION,
            "op": "preflight",
            "result": self.to_result_dict(),
        }


# ---------------------------------------------------------------------------
# git helpers (read-only)
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: str) -> tuple[int, str]:
    """Run a read-only git command. Returns (returncode, stdout).

    Only the trailing newline is stripped — never leading whitespace — because
    ``git status --porcelain`` encodes a file's state in the first two columns,
    where a leading space is significant (e.g. ``" M path"`` for an unstaged
    modification).
    """
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd, capture_output=True, text=True, timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 1, ""
    return proc.returncode, proc.stdout.rstrip("\n")


def _parse_porcelain(output: str) -> tuple[list[str], list[str]]:
    """Split ``git status --porcelain`` output into (dirty_tracked, untracked).

    Untracked entries are ``?? <path>``; everything else (modified, added,
    deleted, renamed) is a tracked change. Rename entries (``orig -> new``) are
    reduced to the new path. Both lists are sorted for deterministic output.
    """
    dirty: list[str] = []
    untracked: list[str] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        status, path = line[:2], line[3:]
        if " -> " in path:  # rename/copy: record the destination path
            path = path.split(" -> ", 1)[1]
        if status == "??":
            untracked.append(path)
        elif status == "!!":  # ignored — never relevant to a lane check
            continue
        else:
            dirty.append(path)
    return sorted(dirty), sorted(untracked)


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------


def run_preflight(
    repo: str = ".",
    *,
    expected_branch: str | None = None,
    expected_base: str | None = None,
    allow_untracked: list[str] | None = None,
) -> PreflightResult:
    """Gather lane state and compute the verdict. Pure of side effects."""
    allow = list(allow_untracked or [])

    code, _ = _git(["rev-parse", "--is-inside-work-tree"], repo)
    if code != 0:
        return PreflightResult(
            worktree=None, branch=None, head=None, upstream=None,
            expected_branch=expected_branch, expected_base=expected_base,
            branch_matches=False, base_is_ancestor=False,
            failures=[Failure("NOT_A_GIT_REPO", f"{repo} is not inside a git work tree.")],
        )

    _, worktree = _git(["rev-parse", "--show-toplevel"], repo)
    _, branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo)
    _, head = _git(["rev-parse", "HEAD"], repo)
    up_code, upstream = _git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], repo)
    upstream_val = upstream if up_code == 0 and upstream else None

    # --untracked-files=all lists nested files individually (git otherwise
    # collapses an untracked directory to its name), so lane-collision files
    # like docs/sdk/x are visible and can be matched against the allow-list.
    _, porcelain = _git(["status", "--porcelain", "--untracked-files=all"], repo)
    dirty_tracked, untracked = _parse_porcelain(porcelain)

    unexpected_untracked = [
        p for p in untracked
        if not any(fnmatch.fnmatch(p, pat) or p.startswith(pat) for pat in allow)
    ]

    branch_matches = expected_branch is None or branch == expected_branch

    if expected_base is None:
        base_is_ancestor = True
    else:
        anc_code, _ = _git(["merge-base", "--is-ancestor", expected_base, "HEAD"], repo)
        base_is_ancestor = anc_code == 0

    failures: list[Failure] = []
    if expected_branch is not None and not branch_matches:
        failures.append(Failure(
            "BRANCH_MISMATCH",
            f"On branch '{branch}', expected '{expected_branch}'.",
        ))
    if dirty_tracked:
        failures.append(Failure(
            "TRACKED_CHANGES",
            f"Worktree has {len(dirty_tracked)} tracked change(s); commit or stash before starting.",
        ))
    if unexpected_untracked:
        failures.append(Failure(
            "UNEXPECTED_UNTRACKED",
            f"{len(unexpected_untracked)} unexpected untracked file(s); "
            "clean up or allow-list before starting.",
        ))
    if expected_base is not None and not base_is_ancestor:
        failures.append(Failure(
            "MISSING_BASE",
            f"Expected base '{expected_base}' is not an ancestor of HEAD.",
        ))

    return PreflightResult(
        worktree=worktree or None,
        branch=branch or None,
        head=head or None,
        upstream=upstream_val,
        expected_branch=expected_branch,
        expected_base=expected_base,
        branch_matches=branch_matches,
        base_is_ancestor=base_is_ancestor,
        dirty_tracked=dirty_tracked,
        untracked=untracked,
        unexpected_untracked=unexpected_untracked,
        failures=failures,
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_human(result: PreflightResult) -> str:
    lines: list[str] = []
    verdict = "OK" if result.ok else "FAIL"
    lines.append(f"{PRODUCT_NAME} lane preflight: {verdict}")
    lines.append(f"  worktree: {result.worktree or '(unknown)'}")
    lines.append(f"  branch:   {result.branch or '(unknown)'}")
    lines.append(f"  HEAD:     {result.head or '(unknown)'}")
    lines.append(f"  upstream: {result.upstream or '(none)'}")
    if result.expected_branch is not None:
        mark = "ok" if result.branch_matches else "MISMATCH"
        lines.append(f"  expected branch: {result.expected_branch} [{mark}]")
    if result.expected_base is not None:
        mark = "ok" if result.base_is_ancestor else "MISSING"
        lines.append(f"  expected base:   {result.expected_base} [{mark}]")
    lines.append(f"  tracked changes: {len(result.dirty_tracked)}")
    for p in result.dirty_tracked:
        lines.append(f"    ~ {p}")
    lines.append(f"  untracked: {len(result.untracked)} "
                 f"({len(result.unexpected_untracked)} unexpected)")
    for p in result.unexpected_untracked:
        lines.append(f"    ? {p}")
    for f in result.failures:
        lines.append(f"  FAIL [{f.code}]: {f.message}")
    lines.append(f"  {result.summary}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nexskill preflight",
        description=f"{PRODUCT_NAME} lane isolation preflight: confirm the current "
        "branch/worktree is the expected one before starting work.",
    )
    parser.add_argument("--repo", default=".", help="Repository or worktree path.")
    parser.add_argument("--expected-branch", default=None, help="Branch the lane must be on.")
    parser.add_argument("--expected-base", default=None,
                        help="Ref that must be an ancestor of HEAD (the lane's base).")
    parser.add_argument("--allow-untracked", action="append", default=None, metavar="PATTERN",
                        help="Untracked path or glob to treat as expected (repeatable).")
    parser.add_argument("--json", action="store_true", help="Emit the JSON envelope.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_preflight(
        args.repo,
        expected_branch=args.expected_branch,
        expected_base=args.expected_base,
        allow_untracked=args.allow_untracked,
    )
    if args.json:
        sys.stdout.write(json.dumps(result.to_envelope(), ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(render_human(result) + "\n")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
