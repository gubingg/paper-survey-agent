from __future__ import annotations

from app.graph.state import coerce_field_state

RECEIVE_FIELD_PROBLEM_NODE = "receive_field_problem"
JUDGE_NEED_FILL_NODE = "judge_need_fill"
BUILD_RETRIEVAL_QUERY_NODE = "build_retrieval_query"
RETRIEVE_INTERNAL_EVIDENCE_NODE = "retrieve_internal_evidence"
JUDGE_EVIDENCE_NODE = "judge_evidence"
RETRY_OR_STOP_NODE = "retry_or_stop"
GENERATE_FILLED_FIELD_NODE = "generate_filled_field"
OPTIONAL_HUMAN_REVIEW_NODE = "optional_human_review"
RETURN_TO_MAIN_WORKFLOW_NODE = "return_to_main_workflow"


def route_after_need_fill(state) -> str:
    graph_state = coerce_field_state(state)
    return BUILD_RETRIEVAL_QUERY_NODE if graph_state.need_fill else RETURN_TO_MAIN_WORKFLOW_NODE


def route_after_judge_evidence(state) -> str:
    graph_state = coerce_field_state(state)
    return GENERATE_FILLED_FIELD_NODE if graph_state.evidence_sufficient else RETRY_OR_STOP_NODE


def route_after_retry(state) -> str:
    graph_state = coerce_field_state(state)
    return BUILD_RETRIEVAL_QUERY_NODE if graph_state.fill_status == "retry" else OPTIONAL_HUMAN_REVIEW_NODE
