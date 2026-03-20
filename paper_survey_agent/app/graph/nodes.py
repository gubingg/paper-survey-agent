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
from app.services.gap_service import GapService
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
gap_service = GapService()
export_service = ExportService()


def create_project_node(state):
    """Load project context before workflow execution."""

    graph_state = coerce_main_state(state)
    with SessionLocal() as db:
        project = crud.get_project(db, graph_state.project_id)
        if project is None:
            raise ValueError(f"Project not found: {graph_state.project_id}")
    return {
        "logs": append_log(graph_state.logs, f"Loaded project {graph_state.project_id}."),
    }


def parse_papers_node(state):
    """Parse project PDFs and persist parsed artifacts."""

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
    """Generate chunks after PDF parsing."""

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
    """Extract normalized paper cards and persist them."""

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
    """Index chunks into the vector store."""

    graph_state = coerce_main_state(state)
    chunks = [chunk for paper in graph_state.parsed_papers for chunk in paper.chunks]
    index_result = vector_store_service.index_chunks(graph_state.project_id, chunks)
    return {
        "logs": append_log(graph_state.logs, f"Vector index result: {index_result['reason']}"),
    }


def detect_problem_fields_node(state):
    """Detect suspicious fields that need the completion agent."""

    graph_state = coerce_main_state(state)
    problem_fields = []
    for schema in graph_state.paper_schemas:
        try:
            problem_fields.extend(field_completion_service.detect_problem_fields(schema))
        except Exception as exc:
            logger.exception("Field problem detection failed for %s", schema.paper_id)
    return {
        "problem_fields": problem_fields,
        "logs": append_log(graph_state.logs, f"Detected {len(problem_fields)} problematic fields."),
    }


def run_field_completion_agent_node(state):
    """Run the field completion subgraph for each detected field problem."""

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
    """Build the cross-paper comparison result."""

    graph_state = coerce_main_state(state)
    compare_result = compare_service.build_compare_result(graph_state.paper_schemas, topic=graph_state.topic)
    return {
        "compare_result": compare_result,
        "logs": append_log(graph_state.logs, "Built comparison table and trend summary."),
    }


def generate_gap_candidates_node(state):
    """Generate initial gap candidates from compare output and paper cards."""

    graph_state = coerce_main_state(state)
    candidates = gap_service.generate_gap_candidates(
        project_id=graph_state.project_id,
        paper_schemas=graph_state.paper_schemas,
        compare_result=graph_state.compare_result,
    )
    return {
        "gap_candidates": candidates,
        "logs": append_log(graph_state.logs, f"Generated {len(candidates)} preliminary gap candidates."),
    }


def run_gap_validation_agent_node(state):
    """Run the gap validation subgraph for each candidate."""

    graph_state = coerce_main_state(state)
    all_chunks = [chunk for paper in graph_state.parsed_papers for chunk in paper.chunks]
    validated_candidates = []
    workflow_logs = list(graph_state.logs)
    for candidate in graph_state.gap_candidates:
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
                    )
                )
            )
        except Exception as exc:
            logger.exception("Gap validation failed for %s", candidate.gap_id)
            workflow_logs = append_log(workflow_logs, f"Gap validation failed for {candidate.gap_id}: {exc}")
            candidate.validation_result = "证据弱"
            candidate.requires_human_review = True
            candidate.evidence_summary = [*candidate.evidence_summary, f"Gap validation failed: {exc}"]
            validated_candidates.append(candidate)

    with SessionLocal() as db:
        crud.replace_gap_candidates(db, graph_state.project_id, validated_candidates)

    return {
        "gap_candidates": validated_candidates,
        "logs": append_log(workflow_logs, f"Validated {len(validated_candidates)} gap candidates."),
    }


def human_review_node(state):
    """Collect low-risk outputs and leave high-risk ones pending for manual review."""

    graph_state = coerce_main_state(state)
    approved_gaps = []
    updated_gaps = []
    for gap in graph_state.gap_candidates:
        if gap.validation_result == "成立" and not gap.requires_human_review and gap.status != "rejected":
            gap.status = "approved"
            approved_gaps.append(gap)
        else:
            gap.status = gap.status if gap.status == "rejected" else "pending"
        updated_gaps.append(gap)

    with SessionLocal() as db:
        crud.replace_gap_candidates(db, graph_state.project_id, updated_gaps)

    return {
        "gap_candidates": updated_gaps,
        "approved_gaps": approved_gaps,
        "logs": append_log(graph_state.logs, "Prepared high-risk outputs for human review."),
    }


def export_results_node(state):
    """Export project output based on the target type."""

    graph_state = coerce_main_state(state)
    export_type = graph_state.target_type if graph_state.target_type in {"survey", "meeting_outline", "gap_analysis"} else "meeting_outline"
    export_payload = export_service.export(
        project_id=graph_state.project_id,
        export_type=export_type,
        topic=graph_state.topic,
        paper_schemas=graph_state.paper_schemas,
        compare_result=graph_state.compare_result,
        gap_candidates=graph_state.gap_candidates,
    )
    return {
        "export_payload": export_payload.model_dump(),
        "logs": append_log(graph_state.logs, f"Exported {export_type} to {export_payload.file_path}."),
    }
