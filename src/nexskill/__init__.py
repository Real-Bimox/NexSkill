"""NexSkill - guides the work, selects the right skill path, proves the result.

Public package for the NexSkill command family. This module intentionally keeps
no heavy imports at the top level so that ``import nexskill`` stays cheap.
"""

from .contracts import (
    ENVELOPE_SCHEMA_VERSION,
    EVIDENCE_SCHEMA_VERSION,
    PRODUCT_NAME,
    REPORT_SCHEMA_VERSION,
    SKILL_SCHEMA_VERSION,
    CONFIG_SCHEMA_VERSION,
    NexSkillError,
)

__version__ = "1.0.0"

__all__ = [
    "__version__",
    "ENVELOPE_SCHEMA_VERSION",
    "EVIDENCE_SCHEMA_VERSION",
    "PRODUCT_NAME",
    "REPORT_SCHEMA_VERSION",
    "SKILL_SCHEMA_VERSION",
    "CONFIG_SCHEMA_VERSION",
    "NexSkillError",
]
