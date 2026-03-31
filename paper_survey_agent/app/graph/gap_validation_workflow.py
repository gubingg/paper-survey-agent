from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.graph.gap_validation_edges import (
    CHECK_COVERAGE_NODE,
    EXTERNAL_SEARCH_IF_NEEDED_NODE,
    FINAL_GAP_DECISION_NODE,
    HUMAN_REVIEW_GATE_NODE,
    NORMALIZE_GAP_CANDIDATE_NODE,
    RECEIVE_GAP_CANDIDATE_NODE,
    RETRIEVE_COUNTER_EVIDENCE_NODE,
    RETRIEVE_SUPPORT_EVIDENCE_NODE,
    RETURN_GAP_RESULT_NODE,
    JUDGE_SUPPORT_STRENGTH_NODE,
)
from app.graph.gap_validation_nodes import (
    check_coverage_node,
    external_search_if_needed_node,
    final_gap_decision_node,
    human_review_gate_node,
    normalize_gap_candidate_node,
    receive_gap_candidate_node,
    retrieve_counter_evidence_node,
    retrieve_support_evidence_node,
    return_gap_result_node,
    judge_support_strength_node,
)
from app.schemas.graph_state import GapValidationAgentState
from app.services.gap_validation_service import GapValidationService

validation_service = GapValidationService()


@lru_cache(maxsize=1)
def get_gap_validation_workflow():
    """Compile and cache the strict gap validation subgraph."""

    builder = StateGraph(GapValidationAgentState)
    builder.add_node(RECEIVE_GAP_CANDIDATE_NODE, receive_gap_candidate_node)
    builder.add_node(NORMALIZE_GAP_CANDIDATE_NODE, normalize_gap_candidate_node)
    builder.add_node(RETRIEVE_SUPPORT_EVIDENCE_NODE, retrieve_support_evidence_node)
    builder.add_node(JUDGE_SUPPORT_STRENGTH_NODE, judge_support_strength_node)
    builder.add_node(RETRIEVE_COUNTER_EVIDENCE_NODE, retrieve_counter_evidence_node)
    builder.add_node(CHECK_COVERAGE_NODE, check_coverage_node)
    builder.add_node(EXTERNAL_SEARCH_IF_NEEDED_NODE, external_search_if_needed_node)
    builder.add_node(FINAL_GAP_DECISION_NODE, final_gap_decision_node)
    builder.add_node(HUMAN_REVIEW_GATE_NODE, human_review_gate_node)
    builder.add_node(RETURN_GAP_RESULT_NODE, return_gap_result_node)

    builder.add_edge(START, RECEIVE_GAP_CANDIDATE_NODE)
    builder.add_edge(RECEIVE_GAP_CANDIDATE_NODE, NORMALIZE_GAP_CANDIDATE_NODE)
    builder.add_edge(NORMALIZE_GAP_CANDIDATE_NODE, RETRIEVE_SUPPORT_EVIDENCE_NODE)
    builder.add_edge(RETRIEVE_SUPPORT_EVIDENCE_NODE, JUDGE_SUPPORT_STRENGTH_NODE)
    builder.add_edge(JUDGE_SUPPORT_STRENGTH_NODE, RETRIEVE_COUNTER_EVIDENCE_NODE)
    builder.add_edge(RETRIEVE_COUNTER_EVIDENCE_NODE, CHECK_COVERAGE_NODE)
    builder.add_edge(CHECK_COVERAGE_NODE, EXTERNAL_SEARCH_IF_NEEDED_NODE)
    builder.add_edge(EXTERNAL_SEARCH_IF_NEEDED_NODE, FINAL_GAP_DECISION_NODE)
    builder.add_edge(FINAL_GAP_DECISION_NODE, HUMAN_REVIEW_GATE_NODE)
    builder.add_edge(HUMAN_REVIEW_GATE_NODE, RETURN_GAP_RESULT_NODE)
    builder.add_edge(RETURN_GAP_RESULT_NODE, END)
    return builder.compile()


def run_gap_validation_agent(initial_state: GapValidationAgentState):
    """Run the strict gap validation agent and return the validated candidate."""

    workflow = get_gap_validation_workflow()
    result = workflow.invoke(initial_state.model_dump())
    final_state = GapValidationAgentState.model_validate(result)
    candidate = final_state.candidate
    return validation_service.attach_validation(
        candidate=candidate,
        supporting=final_state.supporting_evidence,
        counter=final_state.counter_evidence,
        coverage_count=final_state.coverage_count,
        validation_result=final_state.validation_result or "insufficient_evidence",
        confidence=final_state.confidence,
        requires_human_review=final_state.requires_human_review,
        validation_level="strict",
        validation_reason=getattr(final_state, "validation_reason", ""),
        normalized_gap=final_state.normalized_gap,
        support_strength=final_state.support_strength,
        support_reason=final_state.support_reason,
        support_count=final_state.support_count,
        distinct_paper_count=final_state.distinct_paper_count,
        counter_strength=final_state.counter_strength,
        counter_reason=final_state.counter_reason,
        coverage_status=final_state.coverage_status,
        coverage_reason=final_state.coverage_reason,
        coverage_risks=final_state.coverage_risks,
        external_search_used=final_state.external_search_used,
        human_review_reason=final_state.human_review_reason,
    )
