from __future__ import annotations

from app.graph.state import append_log, coerce_gap_state
from app.services.gap_validation_service import GapValidationService
from app.services.vector_store_service import VectorStoreService

vector_store_service = VectorStoreService()
gap_validation_service = GapValidationService()


def receive_gap_candidate_node(state):
    graph_state = coerce_gap_state(state)
    return {
        "logs": append_log(graph_state.logs, f"Received gap candidate {graph_state.gap_id}."),
    }


def decompose_gap_node(state):
    graph_state = coerce_gap_state(state)
    verification_points = gap_validation_service.decompose_gap(graph_state.candidate)
    return {
        "verification_points": verification_points,
        "logs": append_log(graph_state.logs, f"Decomposed gap into {len(verification_points)} verification points."),
    }


def retrieve_supporting_evidence_node(state):
    graph_state = coerce_gap_state(state)
    evidence = []
    for query in graph_state.verification_points[:3]:
        evidence.extend(
            vector_store_service.query_chunks(
                project_id=graph_state.project_id,
                query=query,
                chunks=graph_state.chunks,
                top_k=3,
            )
        )
    dedup = []
    seen: set[tuple[str, str]] = set()
    for item in sorted(evidence, key=lambda x: x.score, reverse=True):
        key = (item.paper_id, item.chunk_id)
        if key not in seen:
            seen.add(key)
            dedup.append(item)
    return {
        "supporting_evidence": dedup[:6],
        "logs": append_log(graph_state.logs, f"Retrieved {len(dedup[:6])} supporting evidence snippets."),
    }


def retrieve_counter_evidence_node(state):
    graph_state = coerce_gap_state(state)
    counter = gap_validation_service.collect_counter_evidence_from_schemas(graph_state.candidate, graph_state.paper_schemas)
    for query in gap_validation_service.build_counter_queries(graph_state.candidate):
        counter.extend(
            vector_store_service.query_chunks(
                project_id=graph_state.project_id,
                query=query,
                chunks=graph_state.chunks,
                top_k=2,
            )
        )
    dedup = []
    seen: set[tuple[str, str, str]] = set()
    for item in counter:
        key = (item.paper_id, item.chunk_id, item.content[:50])
        if key not in seen:
            seen.add(key)
            dedup.append(item)
    return {
        "counter_evidence": dedup[:6],
        "logs": append_log(graph_state.logs, f"Retrieved {len(dedup[:6])} counter or conflict evidence snippets."),
    }


def check_coverage_node(state):
    graph_state = coerce_gap_state(state)
    coverage_count = gap_validation_service.check_coverage(graph_state.supporting_evidence)
    return {
        "coverage_count": coverage_count,
        "logs": append_log(graph_state.logs, f"Supporting evidence covers {coverage_count} papers."),
    }


def judge_gap_evidence_node(state):
    graph_state = coerce_gap_state(state)
    validation_result, confidence, requires_review = gap_validation_service.judge_gap_evidence(
        graph_state.supporting_evidence,
        graph_state.counter_evidence,
        graph_state.coverage_count,
    )
    return {
        "validation_result": validation_result,
        "confidence": confidence,
        "requires_human_review": requires_review,
        "evidence_sufficient": validation_result in {"成立", "有冲突", "不成立"},
        "logs": append_log(graph_state.logs, f"Gap validation result: {validation_result} (confidence={confidence})."),
    }


def retry_or_finalize_gap_node(state):
    graph_state = coerce_gap_state(state)
    next_retry = graph_state.retry_count + 1
    return {
        "retry_count": next_retry,
        "logs": append_log(graph_state.logs, f"Gap validation retry #{next_retry}."),
    }


def optional_gap_human_review_node(state):
    graph_state = coerce_gap_state(state)
    message = "Gap validation requires human review." if graph_state.requires_human_review else "Gap validation auto-cleared."
    return {
        "logs": append_log(graph_state.logs, message),
    }


def return_gap_result_node(state):
    graph_state = coerce_gap_state(state)
    return {
        "logs": append_log(graph_state.logs, "Returning validated gap candidate to main workflow."),
    }
