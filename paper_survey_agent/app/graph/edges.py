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
RUN_GAP_VALIDATION_AGENT_NODE = "run_gap_validation_agent"
HUMAN_REVIEW_NODE = "human_review"
EXPORT_NODE = "export_results"


def route_after_problem_detection(state) -> str:
    graph_state = coerce_main_state(state)
    return RUN_FIELD_COMPLETION_AGENT_NODE if graph_state.problem_fields else COMPARE_NODE


def route_after_gap_generation(state) -> str:
    graph_state = coerce_main_state(state)
    if graph_state.enable_gap_analysis and graph_state.gap_candidates:
        return RUN_GAP_VALIDATION_AGENT_NODE
    return HUMAN_REVIEW_NODE
