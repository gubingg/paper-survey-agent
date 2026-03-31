from __future__ import annotations

from app.graph.state import coerce_main_state

CREATE_PROJECT_NODE = "create_project"
PARSE_NODE = "parse_papers"
CHUNK_NODE = "chunk_papers"
EXTRACT_NODE = "extract_schema"
INDEX_NODE = "index_chunks"
DETECT_PROBLEM_FIELDS_NODE = "detect_problem_fields"
RUN_FIELD_COMPLETION_AGENT_NODE = "run_field_completion_agent"
COMPARE_NODE = "compare_papers"
GENERATE_GAP_CANDIDATES_NODE = "generate_gap_candidates"
LIGHT_GAP_VALIDATION_NODE = "light_gap_validation"
STRICT_GAP_VALIDATION_NODE = "strict_gap_validation"
HUMAN_REVIEW_NODE = "human_review"
EXPORT_NODE = "export_results"


def route_after_problem_detection(state) -> str:
    graph_state = coerce_main_state(state)
    return RUN_FIELD_COMPLETION_AGENT_NODE if graph_state.problem_fields else COMPARE_NODE


def route_after_gap_generation(state) -> str:
    graph_state = coerce_main_state(state)
    effective_level = graph_state.effective_validation_level or graph_state.gap_validation_level
    if not graph_state.gap_candidates_raw:
        return HUMAN_REVIEW_NODE
    if effective_level == "off":
        return HUMAN_REVIEW_NODE
    if effective_level == "light":
        return LIGHT_GAP_VALIDATION_NODE
    if effective_level == "strict":
        return STRICT_GAP_VALIDATION_NODE
    return LIGHT_GAP_VALIDATION_NODE
