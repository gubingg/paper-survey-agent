from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.graph.edges import (
    CHUNK_NODE,
    COMPARE_NODE,
    CREATE_PROJECT_NODE,
    DETECT_PROBLEM_FIELDS_NODE,
    EXPORT_NODE,
    EXTRACT_NODE,
    GENERATE_GAP_CANDIDATES_NODE,
    HUMAN_REVIEW_NODE,
    INDEX_NODE,
    PARSE_NODE,
    RUN_FIELD_COMPLETION_AGENT_NODE,
    RUN_GAP_VALIDATION_AGENT_NODE,
    route_after_gap_generation,
    route_after_problem_detection,
)
from app.graph.nodes import (
    chunk_papers_node,
    compare_papers_node,
    create_project_node,
    detect_problem_fields_node,
    export_results_node,
    extract_schema_node,
    generate_gap_candidates_node,
    human_review_node,
    index_chunks_node,
    parse_papers_node,
    run_field_completion_agent_node,
    run_gap_validation_agent_node,
)
from app.schemas.graph_state import MainWorkflowState


@lru_cache(maxsize=1)
def get_workflow():
    """Compile and cache the main workflow."""

    builder = StateGraph(MainWorkflowState)
    builder.add_node(CREATE_PROJECT_NODE, create_project_node)
    builder.add_node(PARSE_NODE, parse_papers_node)
    builder.add_node(CHUNK_NODE, chunk_papers_node)
    builder.add_node(EXTRACT_NODE, extract_schema_node)
    builder.add_node(INDEX_NODE, index_chunks_node)
    builder.add_node(DETECT_PROBLEM_FIELDS_NODE, detect_problem_fields_node)
    builder.add_node(RUN_FIELD_COMPLETION_AGENT_NODE, run_field_completion_agent_node)
    builder.add_node(COMPARE_NODE, compare_papers_node)
    builder.add_node(GENERATE_GAP_CANDIDATES_NODE, generate_gap_candidates_node)
    builder.add_node(RUN_GAP_VALIDATION_AGENT_NODE, run_gap_validation_agent_node)
    builder.add_node(HUMAN_REVIEW_NODE, human_review_node)
    builder.add_node(EXPORT_NODE, export_results_node)

    builder.add_edge(START, CREATE_PROJECT_NODE)
    builder.add_edge(CREATE_PROJECT_NODE, PARSE_NODE)
    builder.add_edge(PARSE_NODE, CHUNK_NODE)
    builder.add_edge(CHUNK_NODE, EXTRACT_NODE)
    builder.add_edge(EXTRACT_NODE, INDEX_NODE)
    builder.add_edge(INDEX_NODE, DETECT_PROBLEM_FIELDS_NODE)
    builder.add_conditional_edges(
        DETECT_PROBLEM_FIELDS_NODE,
        route_after_problem_detection,
        {
            RUN_FIELD_COMPLETION_AGENT_NODE: RUN_FIELD_COMPLETION_AGENT_NODE,
            COMPARE_NODE: COMPARE_NODE,
        },
    )
    builder.add_edge(RUN_FIELD_COMPLETION_AGENT_NODE, COMPARE_NODE)
    builder.add_edge(COMPARE_NODE, GENERATE_GAP_CANDIDATES_NODE)
    builder.add_conditional_edges(
        GENERATE_GAP_CANDIDATES_NODE,
        route_after_gap_generation,
        {
            RUN_GAP_VALIDATION_AGENT_NODE: RUN_GAP_VALIDATION_AGENT_NODE,
            HUMAN_REVIEW_NODE: HUMAN_REVIEW_NODE,
        },
    )
    builder.add_edge(RUN_GAP_VALIDATION_AGENT_NODE, HUMAN_REVIEW_NODE)
    builder.add_edge(HUMAN_REVIEW_NODE, EXPORT_NODE)
    builder.add_edge(EXPORT_NODE, END)
    return builder.compile()


def run_workflow(initial_state: MainWorkflowState) -> MainWorkflowState:
    """Run the workflow and validate the final state."""

    workflow = get_workflow()
    result = workflow.invoke(initial_state.model_dump())
    return MainWorkflowState.model_validate(result)
