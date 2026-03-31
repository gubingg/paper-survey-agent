from __future__ import annotations

from app.graph.state import append_log, coerce_gap_state
from app.services.gap_validation_service import GapValidationService
from app.services.vector_store_service import VectorStoreService

vector_store_service = VectorStoreService()
gap_validation_service = GapValidationService()


def _dedup_evidence(items, limit: int) -> list:
    deduped = []
    seen: set[tuple[str, str, int, int]] = set()
    for item in sorted(items, key=lambda evidence: evidence.score, reverse=True):
        key = (item.paper_id, item.chunk_id, item.page_start, item.page_end)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= limit:
            break
    return deduped


def receive_gap_candidate_node(state):
    graph_state = coerce_gap_state(state)
    return {
        "logs": append_log(graph_state.logs, f"Received gap candidate {graph_state.gap_id}."),
    }


def normalize_gap_candidate_node(state):
    graph_state = coerce_gap_state(state)
    normalized_gap = gap_validation_service.normalize_gap_candidate(
        graph_state.candidate,
        graph_state.compare_result,
        graph_state.paper_schemas,
    )
    support_queries = gap_validation_service.build_support_queries(normalized_gap)
    counter_queries = gap_validation_service.build_counter_queries(graph_state.candidate, normalized_gap)
    verification_points = gap_validation_service.decompose_gap(graph_state.candidate)
    return {
        "normalized_gap": normalized_gap,
        "verification_points": verification_points,
        "support_queries": support_queries,
        "counter_queries": counter_queries,
        "logs": append_log(graph_state.logs, f"Normalized gap candidate into a structured claim with {len(support_queries)} support queries."),
    }


def retrieve_support_evidence_node(state):
    graph_state = coerce_gap_state(state)
    evidence = []
    for query in graph_state.support_queries[:3]:
        evidence.extend(
            vector_store_service.retrieve_evidence(
                project_id=graph_state.project_id,
                query=query,
                chunks=graph_state.chunks,
                evidence_type="support",
                top_k=4,
            )
        )
    deduped = _dedup_evidence(evidence, limit=8)
    return {
        "supporting_evidence": deduped,
        "logs": append_log(graph_state.logs, f"Retrieved {len(deduped)} support evidence snippets for strict validation."),
    }


def judge_support_strength_node(state):
    graph_state = coerce_gap_state(state)
    support_result = gap_validation_service.judge_support_strength(graph_state.supporting_evidence)
    return {
        "support_strength": support_result["support_strength"],
        "support_reason": support_result["support_reason"],
        "support_count": support_result["support_count"],
        "distinct_paper_count": support_result["distinct_paper_count"],
        "logs": append_log(graph_state.logs, f"Support strength judged as {support_result['support_strength']}."),
    }


def retrieve_counter_evidence_node(state):
    graph_state = coerce_gap_state(state)
    counter = gap_validation_service.collect_counter_evidence_from_schemas(graph_state.candidate, graph_state.paper_schemas)
    for query in graph_state.counter_queries[:3]:
        counter.extend(
            vector_store_service.retrieve_evidence(
                project_id=graph_state.project_id,
                query=query,
                chunks=graph_state.chunks,
                evidence_type="counter",
                top_k=3,
            )
        )
    deduped = _dedup_evidence(counter, limit=6)
    counter_result = gap_validation_service.summarize_counter_evidence(deduped)
    return {
        "counter_evidence": deduped,
        "counter_strength": counter_result["counter_strength"],
        "counter_reason": counter_result["counter_reason"],
        "logs": append_log(graph_state.logs, f"Counter-evidence judged as {counter_result['counter_strength']}."),
    }


def check_coverage_node(state):
    graph_state = coerce_gap_state(state)
    coverage_result = gap_validation_service.assess_coverage(graph_state.supporting_evidence, graph_state.paper_schemas)
    coverage_count = gap_validation_service.check_coverage(graph_state.supporting_evidence)
    return {
        "coverage_count": coverage_count,
        "coverage_status": coverage_result["coverage_status"],
        "coverage_reason": coverage_result["coverage_reason"],
        "coverage_risks": coverage_result["coverage_risks"],
        "logs": append_log(graph_state.logs, f"Coverage assessed as {coverage_result['coverage_status']} across {coverage_count} paper(s)."),
    }


def external_search_if_needed_node(state):
    graph_state = coerce_gap_state(state)
    needed = gap_validation_service.should_trigger_external_search(
        graph_state.candidate,
        graph_state.support_strength,
        graph_state.counter_strength,
        graph_state.coverage_status,
    )
    if needed and graph_state.enable_external_search:
        message = "External search was requested by policy, but no external search backend is configured in this workflow yet."
    elif needed:
        message = "External search is recommended for this candidate, but the current run keeps validation inside the project evidence base."
    else:
        message = "External search is not needed for this candidate."
    return {
        "external_search_used": False,
        "logs": append_log(graph_state.logs, message),
    }


def final_gap_decision_node(state):
    graph_state = coerce_gap_state(state)
    validation_result, confidence, validation_reason = gap_validation_service.final_gap_decision(
        graph_state.support_strength,
        graph_state.counter_strength,
        graph_state.coverage_status,
    )
    return {
        "validation_result": validation_result,
        "confidence": confidence,
        "validation_reason": validation_reason,
        "evidence_sufficient": validation_result in {"confirmed_gap", "likely_gap", "rejected"},
        "logs": append_log(graph_state.logs, f"Strict decision: {validation_result} (confidence={confidence})."),
    }


def human_review_gate_node(state):
    graph_state = coerce_gap_state(state)
    requires_human_review, human_review_reason = gap_validation_service.human_review_gate(
        graph_state.validation_result or "insufficient_evidence",
        graph_state.support_strength,
        graph_state.counter_strength,
        graph_state.coverage_status,
        graph_state.enable_external_search and not graph_state.external_search_used,
    )
    message = "Strict gap validation requires human review." if requires_human_review else "Strict gap validation passed without human review."
    return {
        "requires_human_review": requires_human_review,
        "human_review_reason": human_review_reason,
        "logs": append_log(graph_state.logs, message),
    }


def return_gap_result_node(state):
    graph_state = coerce_gap_state(state)
    return {
        "logs": append_log(graph_state.logs, "Returning strict gap validation result to the main workflow."),
    }
