from __future__ import annotations

from typing import Literal

GapValidationLevel = Literal["off", "light", "strict"]


def resolve_gap_validation_level(
    target_type: str,
    user_override: str | None = None,
    project_default: str | None = None,
) -> GapValidationLevel:
    """Resolve the effective gap validation level for one run."""

    allowed = {"off", "light", "strict"}
    if user_override in allowed:
        return user_override  # type: ignore[return-value]
    if project_default in allowed:
        return project_default  # type: ignore[return-value]
    if target_type == "gap_analysis":
        return "strict"
    if target_type in {"survey", "meeting_outline"}:
        return "light"
    return "light"
