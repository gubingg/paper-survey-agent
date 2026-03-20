from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.graph.gap_validation_edges import (
    CHECK_COVERAGE_NODE,
    DECOMPOSE_GAP_NODE,
    JUDGE_GAP_EVIDENCE_NODE,
    OPTIONAL_GAP_HUMAN_REVIEW_NODE,
    RECEIVE_GAP_CANDIDATE_NODE,
    RETRIEVE_COUNTER_EVIDENCE_NODE,
    RETRIEVE_SUPPORTING_EVIDENCE_NODE,
    RETRY_OR_FINALIZE_GAP_NODE,
    RETURN_GAP_RESULT_NODE,
    route_after_gap_judgement,
    route_after_gap_retry,
)
from app.graph.gap_validation_nodes import (
    check_coverage_node,
    decompose_gap_node,
    judge_gap_evidence_node,
    optional_gap_human_review_node,
    receive_gap_candidate_node,
    retrieve_counter_evidence_node,
    retrieve_supporting_evidence_node,
    retry_or_finalize_gap_node,
    return_gap_result_node,
)
from app.schemas.graph_state import GapValidationAgentState
from app.services.gap_validation_service import GapValidationService

validation_service = GapValidationService()


@lru_cache(maxsize=1)
def get_gap_validation_workflow():
    """Compile and cache the gap validation subgraph."""

    builder = StateGraph(GapValidationAgentState)
    builder.add_node(RECEIVE_GAP_CANDIDATE_NODE, receive_gap_candidate_node)
    builder.add_node(DECOMPOSE_GAP_NODE, decompose_gap_node)
    builder.add_node(RETRIEVE_SUPPORTING_EVIDENCE_NODE, retrieve_supporting_evidence_node)
    builder.add_node(RETRIEVE_COUNTER_EVIDENCE_NODE, retrieve_counter_evidence_node)
    builder.add_node(CHECK_COVERAGE_NODE, check_coverage_node)
    builder.add_node(JUDGE_GAP_EVIDENCE_NODE, judge_gap_evidence_node)
    builder.add_node(RETRY_OR_FINALIZE_GAP_NODE, retry_or_finalize_gap_node)
    builder.add_node(OPTIONAL_GAP_HUMAN_REVIEW_NODE, optional_gap_human_review_node)
    builder.add_node(RETURN_GAP_RESULT_NODE, return_gap_result_node)

    builder.add_edge(START, RECEIVE_GAP_CANDIDATE_NODE)
    builder.add_edge(RECEIVE_GAP_CANDIDATE_NODE, DECOMPOSE_GAP_NODE)
    builder.add_edge(DECOMPOSE_GAP_NODE, RETRIEVE_SUPPORTING_EVIDENCE_NODE)
    builder.add_edge(RETRIEVE_SUPPORTING_EVIDENCE_NODE, RETRIEVE_COUNTER_EVIDENCE_NODE)
    builder.add_edge(RETRIEVE_COUNTER_EVIDENCE_NODE, CHECK_COVERAGE_NODE)
    builder.add_edge(CHECK_COVERAGE_NODE, JUDGE_GAP_EVIDENCE_NODE)
    builder.add_conditional_edges(
        JUDGE_GAP_EVIDENCE_NODE,
        route_after_gap_judgement,
        {
            RETRY_OR_FINALIZE_GAP_NODE: RETRY_OR_FINALIZE_GAP_NODE,
            OPTIONAL_GAP_HUMAN_REVIEW_NODE: OPTIONAL_GAP_HUMAN_REVIEW_NODE,
        },
    )
    builder.add_conditional_edges(
        RETRY_OR_FINALIZE_GAP_NODE,
        route_after_gap_retry,
        {
            RETRIEVE_SUPPORTING_EVIDENCE_NODE: RETRIEVE_SUPPORTING_EVIDENCE_NODE,
            OPTIONAL_GAP_HUMAN_REVIEW_NODE: OPTIONAL_GAP_HUMAN_REVIEW_NODE,
        },
    )
    builder.add_edge(OPTIONAL_GAP_HUMAN_REVIEW_NODE, RETURN_GAP_RESULT_NODE)
    builder.add_edge(RETURN_GAP_RESULT_NODE, END)
    return builder.compile()


def run_gap_validation_agent(initial_state: GapValidationAgentState):
    """Run the gap validation agent and return the validated candidate."""

    workflow = get_gap_validation_workflow()
    result = workflow.invoke(initial_state.model_dump())
    final_state = GapValidationAgentState.model_validate(result)
    candidate = final_state.candidate
    return validation_service.attach_validation(
        candidate=candidate,
        supporting=final_state.supporting_evidence,
        counter=final_state.counter_evidence,
        coverage_count=final_state.coverage_count,
        validation_result=final_state.validation_result or "证据弱",
        confidence=final_state.confidence,
        requires_human_review=final_state.requires_human_review,
    )
