from __future__ import annotations

from app.schemas.graph_state import FieldCompletionAgentState, GapValidationAgentState, MainWorkflowState


MainStateLike = MainWorkflowState | dict
FieldStateLike = FieldCompletionAgentState | dict
GapStateLike = GapValidationAgentState | dict


def coerce_main_state(state: MainStateLike) -> MainWorkflowState:
    """Coerce dict-like LangGraph state into the main workflow model."""

    if isinstance(state, MainWorkflowState):
        return state
    return MainWorkflowState.model_validate(state)


def coerce_field_state(state: FieldStateLike) -> FieldCompletionAgentState:
    """Coerce dict-like LangGraph state into the field completion model."""

    if isinstance(state, FieldCompletionAgentState):
        return state
    return FieldCompletionAgentState.model_validate(state)


def coerce_gap_state(state: GapStateLike) -> GapValidationAgentState:
    """Coerce dict-like LangGraph state into the gap validation model."""

    if isinstance(state, GapValidationAgentState):
        return state
    return GapValidationAgentState.model_validate(state)


def append_log(logs: list[str], message: str) -> list[str]:
    """Append a log message and return a new list."""

    return [*logs, message]
