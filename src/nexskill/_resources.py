"""Resolve packaged NexSkill resources (built-in skills, scaffold template).

Runtime resources ship *inside* the ``nexskill`` package under ``resources/`` so
an installed wheel is self-contained. Paths are resolved through
``importlib.resources`` against the package, never relative to a repository root,
so resolution works identically from a source checkout and an installed wheel.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path


def resource_path(*parts: str) -> Path:
    """Return the on-disk path of a resource shipped inside this package.

    ``parts`` are joined under the package's ``resources/`` directory, e.g.
    ``resource_path("skills")`` or ``resource_path("templates", "skill_pack")``.

    NexSkill resources are plain files installed alongside the package, so the
    traversable returned by :func:`importlib.resources.files` is always a real
    filesystem path; we materialize it as a :class:`pathlib.Path` for the
    directory walking and copying the callers do.
    """
    base = resources.files(__package__).joinpath("resources", *parts)
    return Path(str(base))
