from __future__ import annotations

from app.graph.state import coerce_gap_state

RECEIVE_GAP_CANDIDATE_NODE = "receive_gap_candidate"
DECOMPOSE_GAP_NODE = "decompose_gap"
RETRIEVE_SUPPORTING_EVIDENCE_NODE = "retrieve_supporting_evidence"
RETRIEVE_COUNTER_EVIDENCE_NODE = "retrieve_counter_evidence"
CHECK_COVERAGE_NODE = "check_coverage"
JUDGE_GAP_EVIDENCE_NODE = "judge_gap_evidence"
RETRY_OR_FINALIZE_GAP_NODE = "retry_or_finalize_gap"
OPTIONAL_GAP_HUMAN_REVIEW_NODE = "optional_gap_human_review"
RETURN_GAP_RESULT_NODE = "return_gap_result"


def route_after_gap_judgement(state) -> str:
    graph_state = coerce_gap_state(state)
    if graph_state.validation_result == "证据弱" and graph_state.retry_count < 2:
        return RETRY_OR_FINALIZE_GAP_NODE
    return OPTIONAL_GAP_HUMAN_REVIEW_NODE


def route_after_gap_retry(state) -> str:
    graph_state = coerce_gap_state(state)
    if graph_state.retry_count <= 2 and graph_state.validation_result == "证据弱":
        return RETRIEVE_SUPPORTING_EVIDENCE_NODE
    return OPTIONAL_GAP_HUMAN_REVIEW_NODE
