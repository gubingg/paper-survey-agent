from __future__ import annotations

from app.db import crud
from app.db.session import SessionLocal
from app.graph.field_completion_workflow import run_field_completion_agent
from app.graph.gap_validation_workflow import run_gap_validation_agent
from app.graph.state import append_log, coerce_main_state
from app.schemas.agent_schema import FieldCompletionResult
from app.schemas.graph_state import FieldCompletionAgentState, GapValidationAgentState
from app.services.compare_service import CompareService
from app.services.export_service import ExportService
from app.services.extraction_service import ExtractionService
from app.services.field_completion_service import FieldCompletionService
from app.services.gap_validation_service import GapValidationService
from app.services.pdf_service import PDFService
from app.services.vector_store_service import VectorStoreService
from app.utils.chunk_utils import build_chunks
from app.utils.file_utils import save_json_artifact
from app.utils.logger import get_logger

logger = get_logger(__name__)
pdf_service = PDFService()
extraction_service = ExtractionService()
vector_store_service = VectorStoreService()
compare_service = CompareService()
field_completion_service = FieldCompletionService()
gap_validation_service = GapValidationService()
export_service = ExportService()


CORE_TASK_TYPES = {"survey", "meeting_outline", "gap_analysis"}


def _effective_validation_level(graph_state) -> str:
    return graph_state.effective_validation_level or graph_state.gap_validation_level or "light"


def _task_type(graph_state) -> str:
    return graph_state.target_type if graph_state.target_type in CORE_TASK_TYPES else "meeting_outline"


def create_project_node(state):
    graph_state = coerce_main_state(state)
    with SessionLocal() as db:
        project = crud.get_project(db, graph_state.project_id)
        if project is None:
            raise ValueError(f"Project not found: {graph_state.project_id}")
    return {"logs": append_log(graph_state.logs, f"Loaded project {graph_state.project_id}.")}


def parse_papers_node(state):
    graph_state = coerce_main_state(state)
    with SessionLocal() as db:
        papers = crud.list_project_papers(db, graph_state.project_id)
        parsed_papers = []
        paper_ids = []
        for paper in papers:
            parsed = pdf_service.parse_pdf(paper.file_path, paper.id)
            save_json_artifact(graph_state.project_id, f"{paper.id}.json", parsed.model_dump())
            crud.update_paper_metadata(db, paper.id, title=parsed.title_guess)
            parsed_papers.append(parsed)
            paper_ids.append(paper.id)
    return {
        "parsed_papers": parsed_papers,
        "paper_ids": paper_ids,
        "logs": append_log(graph_state.logs, f"Parsed {len(parsed_papers)} papers."),
    }


def chunk_papers_node(state):
    graph_state = coerce_main_state(state)
    updated_papers = []
    with SessionLocal() as db:
        for parsed_paper in graph_state.parsed_papers:
            parsed_paper.chunks = build_chunks(parsed_paper.paper_id, parsed_paper.pages)
            crud.replace_paper_chunks(db, parsed_paper.paper_id, parsed_paper.chunks)
            updated_papers.append(parsed_paper)
    return {
        "parsed_papers": updated_papers,
        "logs": append_log(graph_state.logs, "Built chunks for parsed papers."),
    }


def extract_schema_node(state):
    """extract-fields skill: structured field extraction from each paper."""

    graph_state = coerce_main_state(state)
    paper_schemas = []
    workflow_logs = list(graph_state.logs)
    with SessionLocal() as db:
        for parsed_paper in graph_state.parsed_papers:
            try:
                schema = extraction_service.extract_paper_schema(parsed_paper)
                crud.upsert_paper_schema(db, schema)
                paper_schemas.append(schema)
            except Exception as exc:
                logger.exception("Schema extraction failed for %s", parsed_paper.paper_id)
                workflow_logs = append_log(workflow_logs, f"Schema extraction failed for {parsed_paper.paper_id}: {exc}")
    return {
        "paper_schemas": paper_schemas,
        "logs": append_log(workflow_logs, f"Extracted schema for {len(paper_schemas)} papers."),
    }


def index_chunks_node(state):
    graph_state = coerce_main_state(state)
    chunks = [chunk for paper in graph_state.parsed_papers for chunk in paper.chunks]
    index_result = vector_store_service.index_chunks(graph_state.project_id, chunks)
    return {"logs": append_log(graph_state.logs, f"Vector index result: {index_result['reason']}")}


def detect_problem_fields_node(state):
    graph_state = coerce_main_state(state)
    problem_fields = []
    for schema in graph_state.paper_schemas:
        try:
            problem_fields.extend(field_completion_service.detect_problem_fields(schema))
        except Exception:
            logger.exception("Field problem detection failed for %s", schema.paper_id)
    return {
        "problem_fields": problem_fields,
        "logs": append_log(graph_state.logs, f"Detected {len(problem_fields)} problematic fields."),
    }


def run_field_completion_agent_node(state):
    """retrieve-evidence skill: retrieve field-level evidence for schema completion."""

    graph_state = coerce_main_state(state)
    schema_map = {schema.paper_id: schema for schema in graph_state.paper_schemas}
    parsed_map = {paper.paper_id: paper for paper in graph_state.parsed_papers}
    completion_results = list(graph_state.field_completion_results)
    workflow_logs = list(graph_state.logs)

    with SessionLocal() as db:
        for problem in graph_state.problem_fields:
            parsed_paper = parsed_map.get(problem.paper_id)
            if parsed_paper is None:
                continue
            try:
                result = run_field_completion_agent(
                    FieldCompletionAgentState(
                        project_id=graph_state.project_id,
                        paper_id=problem.paper_id,
                        field_name=problem.field_name,
                        current_value=problem.current_value,
                        chunks=parsed_paper.chunks,
                    )
                )
            except Exception as exc:
                logger.exception("Field completion failed for %s:%s", problem.paper_id, problem.field_name)
                workflow_logs = append_log(workflow_logs, f"Field completion failed for {problem.paper_id}:{problem.field_name}: {exc}")
                result = FieldCompletionResult(
                    paper_id=problem.paper_id,
                    field_name=problem.field_name,
                    original_value=problem.current_value,
                    filled_value=problem.current_value,
                    need_fill=True,
                    fill_status="evidence_insufficient",
                    requires_human_review=True,
                    logs=[f"Field completion failed: {exc}"],
                )
            completion_results.append(result)
            crud.upsert_field_completion_result(db, graph_state.project_id, result)
            updated_schema = field_completion_service.apply_completion_to_schema(schema_map[problem.paper_id], result)
            schema_map[problem.paper_id] = updated_schema
            crud.update_schema_field_value(
                db,
                problem.paper_id,
                problem.field_name,
                getattr(updated_schema, problem.field_name),
                mark_review=result.requires_human_review,
            )

    return {
        "paper_schemas": list(schema_map.values()),
        "field_completion_results": completion_results,
        "logs": append_log(workflow_logs, f"Completed field completion for {len(graph_state.problem_fields)} fields."),
    }


def compare_papers_node(state):
    """compare-papers skill: build cross-paper comparison before raw gap generation."""

    graph_state = coerce_main_state(state)
    compare_result = compare_service.build_compare_result(
        graph_state.paper_schemas,
        topic=graph_state.topic,
        focus_dimensions=graph_state.focus_dimensions,
        user_requirements=graph_state.user_requirements,
    )
    return {
        "compare_result": compare_result,
        "logs": append_log(graph_state.logs, "Built cross-paper comparison, method comparison, and limitation summary."),
    }


def generate_gap_candidates_node(state):
    """compare-papers skill: derive shared raw gap_candidates_raw from cross-paper analysis."""

    graph_state = coerce_main_state(state)
    effective_level = _effective_validation_level(graph_state)
    candidates = compare_service.generate_gap_candidates_raw(
        project_id=graph_state.project_id,
        paper_schemas=graph_state.paper_schemas,
        compare_result=graph_state.compare_result,
        focus_dimensions=graph_state.focus_dimensions,
        user_requirements=graph_state.user_requirements,
    )
    for candidate in candidates:
        candidate.original_statement = candidate.original_statement or candidate.statement
        candidate.validation_level = "raw"
        candidate.validation_result = "raw_candidate"
        candidate.validation_reason = "Shared raw gap generation completed before validation routing."
    final_candidates = candidates if effective_level == "off" else []
    return {
        "gap_candidates_raw": candidates,
        "final_gap_candidates": final_candidates,
        "logs": append_log(
            graph_state.logs,
            f"Generated {len(candidates)} raw gap candidates for task_type {_task_type(graph_state)} with validation level {effective_level}.",
        ),
    }


def light_gap_validation_node(state):
    """validate-gap skill in light mode with retrieve-evidence support retrieval."""

    graph_state = coerce_main_state(state)
    all_chunks = [chunk for paper in graph_state.parsed_papers for chunk in paper.chunks]
    validated_candidates = []
    for candidate in graph_state.gap_candidates_raw:
        query = gap_validation_service.build_light_query(candidate)
        evidence = vector_store_service.retrieve_evidence(
            project_id=graph_state.project_id,
            query=query,
            chunks=all_chunks,
            evidence_type="support",
            top_k=5,
        )
        status, revised_text, reason, confidence = gap_validation_service.judge_light_gap_candidate(candidate, evidence)
        candidate.statement = revised_text
        candidate.validation_result = status
        candidate.validation_level = "light"
        candidate.validation_reason = reason
        candidate.supporting_evidence = evidence[:5]
        candidate.counter_evidence = []
        candidate.coverage_count = gap_validation_service.check_coverage(evidence)
        candidate.coverage_status = "sufficient" if candidate.coverage_count >= 2 else "limited" if evidence else "insufficient"
        candidate.coverage_reason = "One-pass retrieval coverage for light validation."
        candidate.support_strength = "high" if status == "supported" else "medium" if status == "weakened" else "low"
        candidate.support_reason = reason
        candidate.support_count = len(evidence[:5])
        candidate.distinct_paper_count = candidate.coverage_count
        candidate.counter_strength = "low"
        candidate.counter_reason = "Light validation does not run a dedicated counter-evidence search."
        candidate.confidence = confidence
        candidate.requires_human_review = status == "insufficient"
        candidate.human_review_reason = "light validation evidence insufficient" if status == "insufficient" else ""
        candidate.evidence_summary = [*candidate.evidence_summary[:2], reason, f"Light validation result: {status}"]
        validated_candidates.append(candidate)
    return {
        "gap_candidates_light_validated": validated_candidates,
        "validated_gap_candidates": validated_candidates,
        "final_gap_candidates": validated_candidates,
        "logs": append_log(graph_state.logs, f"Light-validated {len(validated_candidates)} gap candidates."),
    }


def strict_gap_validation_node(state):
    """validate-gap skill in strict mode with retrieve-evidence support/counter retrieval."""

    graph_state = coerce_main_state(state)
    all_chunks = [chunk for paper in graph_state.parsed_papers for chunk in paper.chunks]
    validated_candidates = []
    workflow_logs = list(graph_state.logs)
    for candidate in graph_state.gap_candidates_raw:
        try:
            validated_candidates.append(
                run_gap_validation_agent(
                    GapValidationAgentState(
                        project_id=graph_state.project_id,
                        gap_id=candidate.gap_id,
                        gap_statement=candidate.statement,
                        candidate=candidate,
                        compare_result=graph_state.compare_result,
                        paper_schemas=graph_state.paper_schemas,
                        chunks=all_chunks,
                        enable_external_search=graph_state.enable_external_search,
                    )
                )
            )
        except Exception as exc:
            logger.exception("Gap validation failed for %s", candidate.gap_id)
            workflow_logs = append_log(workflow_logs, f"Gap validation failed for {candidate.gap_id}: {exc}")
            candidate.validation_result = "insufficient_evidence"
            candidate.validation_level = "strict"
            candidate.validation_reason = f"Strict validation failed: {exc}"
            candidate.requires_human_review = True
            candidate.human_review_reason = "strict validation execution failure"
            candidate.evidence_summary = [*candidate.evidence_summary, f"Strict validation failed: {exc}"]
            validated_candidates.append(candidate)
    return {
        "gap_candidates_strict_validated": validated_candidates,
        "validated_gap_candidates": validated_candidates,
        "final_gap_candidates": validated_candidates,
        "logs": append_log(workflow_logs, f"Strict-validated {len(validated_candidates)} gap candidates."),
    }


def human_review_node(state):
    graph_state = coerce_main_state(state)
    effective_level = _effective_validation_level(graph_state)
    source_candidates = list(graph_state.final_gap_candidates or graph_state.validated_gap_candidates or graph_state.gap_candidates_raw)
    approved_gaps = []
    updated_gaps = []

    for gap in source_candidates:
        if effective_level == "light":
            if gap.validation_result in {"supported", "weakened"}:
                gap.status = "approved"
                approved_gaps.append(gap)
            elif gap.validation_result == "insufficient":
                gap.status = "pending"
            else:
                gap.status = "pending"
        elif effective_level == "strict":
            if gap.validation_result == "confirmed_gap" and not gap.requires_human_review:
                gap.status = "approved"
                approved_gaps.append(gap)
            elif gap.validation_result == "rejected":
                gap.status = "rejected"
            else:
                gap.status = "pending"
        else:
            gap.status = "approved"
            approved_gaps.append(gap)
        updated_gaps.append(gap)

    with SessionLocal() as db:
        crud.replace_gap_candidates(db, graph_state.project_id, updated_gaps)

    return {
        "validated_gap_candidates": updated_gaps if effective_level != "off" else graph_state.validated_gap_candidates,
        "final_gap_candidates": updated_gaps,
        "approved_gaps": approved_gaps,
        "logs": append_log(graph_state.logs, "Prepared final_gap_candidates and human review queue."),
    }


def export_results_node(state):
    """generate-output skill: organize the final product by task_type, not validation depth."""

    graph_state = coerce_main_state(state)
    task_type = _task_type(graph_state)
    export_payload = export_service.generate_output(
        task_type=task_type,
        project_id=graph_state.project_id,
        topic=graph_state.topic,
        paper_schemas=graph_state.paper_schemas,
        compare_result=graph_state.compare_result,
        gap_candidates=graph_state.final_gap_candidates,
        focus_dimensions=graph_state.focus_dimensions,
        user_requirements=graph_state.user_requirements,
        effective_validation_level=_effective_validation_level(graph_state),
        validation_details=graph_state.validated_gap_candidates,
    )
    return {
        "export_payload": export_payload.model_dump(),
        "logs": append_log(graph_state.logs, f"Exported {task_type} to {export_payload.file_path}."),
    }
