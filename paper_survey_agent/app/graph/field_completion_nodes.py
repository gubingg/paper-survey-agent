from __future__ import annotations

from app.graph.state import append_log, coerce_field_state
from app.services.field_completion_service import FieldCompletionService
from app.services.vector_store_service import VectorStoreService

field_completion_service = FieldCompletionService()
vector_store_service = VectorStoreService()


def receive_field_problem_node(state):
    graph_state = coerce_field_state(state)
    return {
        "logs": append_log(graph_state.logs, f"Received field problem for {graph_state.paper_id}:{graph_state.field_name}."),
    }


def judge_need_fill_node(state):
    graph_state = coerce_field_state(state)
    need_fill, reason = field_completion_service.judge_need_fill(graph_state.current_value)
    return {
        "need_fill": need_fill,
        "problem_reason": reason,
        "logs": append_log(graph_state.logs, f"Need fill decision for {graph_state.field_name}: {need_fill} ({reason})."),
    }


def build_retrieval_query_node(state):
    graph_state = coerce_field_state(state)
    retry_suffix = ""
    if graph_state.retry_count > 0:
        retry_suffix = f" {field_completion_service.refine_query(graph_state.field_name, graph_state.retry_count)}"
    retrieval_query = f"{field_completion_service.build_retrieval_query(graph_state.field_name, graph_state.current_value)}{retry_suffix}".strip()
    return {
        "retrieval_query": retrieval_query,
        "logs": append_log(graph_state.logs, f"Built retrieval query: {retrieval_query}"),
    }


def retrieve_internal_evidence_node(state):
    graph_state = coerce_field_state(state)
    evidence = vector_store_service.retrieve_evidence(
        project_id=graph_state.project_id,
        query=graph_state.retrieval_query,
        chunks=graph_state.chunks,
        evidence_type="field_completion",
        paper_id=graph_state.paper_id,
        top_k=4,
    )
    return {
        "candidate_evidence": evidence,
        "logs": append_log(graph_state.logs, f"Retrieved {len(evidence)} internal evidence snippets."),
    }


def judge_evidence_node(state):
    graph_state = coerce_field_state(state)
    evidence_sufficient = field_completion_service.judge_evidence(graph_state.field_name, graph_state.candidate_evidence)
    return {
        "evidence_sufficient": evidence_sufficient,
        "logs": append_log(graph_state.logs, f"Evidence sufficient: {evidence_sufficient}."),
    }


def retry_or_stop_node(state):
    graph_state = coerce_field_state(state)
    next_retry = graph_state.retry_count + 1
    if next_retry <= 2:
        return {
            "retry_count": next_retry,
            "fill_status": "retry",
            "logs": append_log(graph_state.logs, f"Retrying field completion search, attempt {next_retry}."),
        }

    filled_value, fill_status = field_completion_service.generate_filled_value(
        graph_state.field_name,
        [],
        graph_state.current_value,
    )
    requires_review = field_completion_service.requires_human_review(graph_state.field_name, [], fill_status)
    return {
        "retry_count": next_retry,
        "filled_value": filled_value,
        "fill_status": fill_status,
        "requires_human_review": requires_review,
        "logs": append_log(graph_state.logs, "Evidence remained insufficient after retries."),
    }


def generate_filled_field_node(state):
    graph_state = coerce_field_state(state)
    filled_value, fill_status = field_completion_service.generate_filled_value(
        graph_state.field_name,
        graph_state.candidate_evidence,
        graph_state.current_value,
    )
    requires_review = field_completion_service.requires_human_review(
        graph_state.field_name,
        graph_state.candidate_evidence,
        fill_status,
    )
    return {
        "filled_value": filled_value,
        "fill_status": fill_status,
        "requires_human_review": requires_review,
        "logs": append_log(graph_state.logs, f"Generated field completion result with status {fill_status}."),
    }


def optional_human_review_node(state):
    graph_state = coerce_field_state(state)
    message = "Field completion marked for human review." if graph_state.requires_human_review else "Field completion auto-approved."
    return {
        "logs": append_log(graph_state.logs, message),
    }


def return_to_main_workflow_node(state):
    graph_state = coerce_field_state(state)
    return {
        "logs": append_log(graph_state.logs, "Returning field completion result to main workflow."),
    }
