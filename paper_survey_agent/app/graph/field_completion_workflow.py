from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.graph.field_completion_edges import (
    BUILD_RETRIEVAL_QUERY_NODE,
    GENERATE_FILLED_FIELD_NODE,
    JUDGE_EVIDENCE_NODE,
    JUDGE_NEED_FILL_NODE,
    OPTIONAL_HUMAN_REVIEW_NODE,
    RECEIVE_FIELD_PROBLEM_NODE,
    RETRIEVE_INTERNAL_EVIDENCE_NODE,
    RETRY_OR_STOP_NODE,
    RETURN_TO_MAIN_WORKFLOW_NODE,
    route_after_judge_evidence,
    route_after_need_fill,
    route_after_retry,
)
from app.graph.field_completion_nodes import (
    build_retrieval_query_node,
    generate_filled_field_node,
    judge_evidence_node,
    judge_need_fill_node,
    optional_human_review_node,
    receive_field_problem_node,
    retrieve_internal_evidence_node,
    retry_or_stop_node,
    return_to_main_workflow_node,
)
from app.schemas.graph_state import FieldCompletionAgentState
from app.services.field_completion_service import FieldCompletionService

field_completion_service = FieldCompletionService()


@lru_cache(maxsize=1)
def get_field_completion_workflow():
    """Compile and cache the field completion subgraph."""

    builder = StateGraph(FieldCompletionAgentState)
    builder.add_node(RECEIVE_FIELD_PROBLEM_NODE, receive_field_problem_node)
    builder.add_node(JUDGE_NEED_FILL_NODE, judge_need_fill_node)
    builder.add_node(BUILD_RETRIEVAL_QUERY_NODE, build_retrieval_query_node)
    builder.add_node(RETRIEVE_INTERNAL_EVIDENCE_NODE, retrieve_internal_evidence_node)
    builder.add_node(JUDGE_EVIDENCE_NODE, judge_evidence_node)
    builder.add_node(RETRY_OR_STOP_NODE, retry_or_stop_node)
    builder.add_node(GENERATE_FILLED_FIELD_NODE, generate_filled_field_node)
    builder.add_node(OPTIONAL_HUMAN_REVIEW_NODE, optional_human_review_node)
    builder.add_node(RETURN_TO_MAIN_WORKFLOW_NODE, return_to_main_workflow_node)

    builder.add_edge(START, RECEIVE_FIELD_PROBLEM_NODE)
    builder.add_edge(RECEIVE_FIELD_PROBLEM_NODE, JUDGE_NEED_FILL_NODE)
    builder.add_conditional_edges(
        JUDGE_NEED_FILL_NODE,
        route_after_need_fill,
        {
            BUILD_RETRIEVAL_QUERY_NODE: BUILD_RETRIEVAL_QUERY_NODE,
            RETURN_TO_MAIN_WORKFLOW_NODE: RETURN_TO_MAIN_WORKFLOW_NODE,
        },
    )
    builder.add_edge(BUILD_RETRIEVAL_QUERY_NODE, RETRIEVE_INTERNAL_EVIDENCE_NODE)
    builder.add_edge(RETRIEVE_INTERNAL_EVIDENCE_NODE, JUDGE_EVIDENCE_NODE)
    builder.add_conditional_edges(
        JUDGE_EVIDENCE_NODE,
        route_after_judge_evidence,
        {
            GENERATE_FILLED_FIELD_NODE: GENERATE_FILLED_FIELD_NODE,
            RETRY_OR_STOP_NODE: RETRY_OR_STOP_NODE,
        },
    )
    builder.add_conditional_edges(
        RETRY_OR_STOP_NODE,
        route_after_retry,
        {
            BUILD_RETRIEVAL_QUERY_NODE: BUILD_RETRIEVAL_QUERY_NODE,
            OPTIONAL_HUMAN_REVIEW_NODE: OPTIONAL_HUMAN_REVIEW_NODE,
        },
    )
    builder.add_edge(GENERATE_FILLED_FIELD_NODE, OPTIONAL_HUMAN_REVIEW_NODE)
    builder.add_edge(OPTIONAL_HUMAN_REVIEW_NODE, RETURN_TO_MAIN_WORKFLOW_NODE)
    builder.add_edge(RETURN_TO_MAIN_WORKFLOW_NODE, END)
    return builder.compile()


def run_field_completion_agent(initial_state: FieldCompletionAgentState):
    """Run the field completion agent and return the persisted result model."""

    workflow = get_field_completion_workflow()
    result = workflow.invoke(initial_state.model_dump())
    final_state = FieldCompletionAgentState.model_validate(result)
    return field_completion_service.result_from_state(
        paper_id=final_state.paper_id,
        field_name=final_state.field_name,
        original_value=final_state.current_value,
        need_fill=final_state.need_fill,
        retrieval_query=final_state.retrieval_query,
        evidences=final_state.candidate_evidence,
        retry_count=final_state.retry_count,
        filled_value=final_state.filled_value if final_state.need_fill else final_state.current_value,
        fill_status=final_state.fill_status,
        requires_human_review=final_state.requires_human_review,
        logs=final_state.logs,
    )
