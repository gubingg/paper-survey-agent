from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    EnrichmentRecord,
    FieldCompletionRecord,
    GapCandidateRecord,
    Paper,
    PaperChunkRecord,
    PaperSchemaRecord,
    Project,
    Task,
)
from app.schemas.agent_schema import (
    EvidenceSnippet,
    FieldCompletionResult,
    FieldCompletionReviewRequest,
)
from app.schemas.gap_schema import EnrichmentEvidence, GapCandidate, GapReviewRequest
from app.schemas.paper_schema import PaperChunk, PaperSchema
from app.utils.chunk_utils import extract_year


LIST_FIELDS = {"datasets", "metrics", "limitations", "future_work", "keywords", "strengths"}


def create_project(db: Session, name: str, topic: str, target_type: str) -> Project:
    """Create a project record."""

    project = Project(
        id=f"proj_{uuid.uuid4().hex[:8]}",
        name=name,
        topic=topic,
        target_type=target_type,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_project(db: Session, project_id: str) -> Project | None:
    """Fetch a project by id."""

    return db.get(Project, project_id)


def create_paper(db: Session, project_id: str, file_path: str, title: str = "") -> Paper:
    """Create a paper record."""

    paper = Paper(
        id=f"paper_{uuid.uuid4().hex[:8]}",
        project_id=project_id,
        file_path=file_path,
        title=title,
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper


def get_paper(db: Session, paper_id: str) -> Paper | None:
    """Fetch a paper by id."""

    return db.get(Paper, paper_id)


def list_project_papers(db: Session, project_id: str) -> list[Paper]:
    """List all papers in a project."""

    stmt = select(Paper).where(Paper.project_id == project_id).order_by(Paper.id)
    return list(db.scalars(stmt))


def update_paper_metadata(db: Session, paper_id: str, title: str | None = None, year: int | None = None) -> None:
    """Update extracted paper metadata."""

    paper = get_paper(db, paper_id)
    if paper is None:
        return
    if title:
        paper.title = title
    if year:
        paper.year = year
    db.commit()


def replace_paper_chunks(db: Session, paper_id: str, chunks: list[PaperChunk]) -> None:
    """Replace all stored chunks for a paper."""

    db.query(PaperChunkRecord).filter(PaperChunkRecord.paper_id == paper_id).delete()
    for chunk in chunks:
        db.add(
            PaperChunkRecord(
                id=chunk.chunk_id,
                paper_id=paper_id,
                section=chunk.section,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                content=chunk.content,
            )
        )
    db.commit()


def list_chunks_by_paper(db: Session, paper_id: str) -> list[PaperChunkRecord]:
    """Fetch all chunks for a paper."""

    stmt = select(PaperChunkRecord).where(PaperChunkRecord.paper_id == paper_id).order_by(PaperChunkRecord.page_start)
    return list(db.scalars(stmt))


def list_project_chunks(db: Session, project_id: str) -> list[PaperChunkRecord]:
    """Fetch all chunks for a project."""

    papers = list_project_papers(db, project_id)
    paper_ids = [paper.id for paper in papers]
    if not paper_ids:
        return []
    stmt = select(PaperChunkRecord).where(PaperChunkRecord.paper_id.in_(paper_ids)).order_by(PaperChunkRecord.paper_id)
    return list(db.scalars(stmt))


def _coerce_schema_field(field_name: str, value):
    if field_name in LIST_FIELDS:
        if isinstance(value, list):
            return value
        if value in (None, ""):
            return []
        return [str(value)]
    if isinstance(value, list):
        return "；".join(str(item) for item in value if str(item).strip())
    return value or ""


def _schema_record_to_model(record: PaperSchemaRecord) -> PaperSchema:
    return PaperSchema(
        paper_id=record.paper_id,
        title=record.title,
        year=record.year,
        research_problem=record.research_problem,
        method=record.method,
        method_category=record.method_category,
        datasets=record.datasets or [],
        metrics=record.metrics or [],
        main_results=record.main_results,
        strengths=record.strengths or [],
        limitations=record.limitations or [],
        future_work=record.future_work or [],
        keywords=record.keywords or [],
        needs_review=record.needs_review,
        warnings=record.warnings or [],
    )


def upsert_paper_schema(db: Session, schema: PaperSchema) -> PaperSchemaRecord:
    """Insert or update a structured paper schema."""

    record = db.get(PaperSchemaRecord, schema.paper_id)
    if record is None:
        record = PaperSchemaRecord(paper_id=schema.paper_id)
        db.add(record)

    record.title = schema.title
    record.year = schema.year
    record.research_problem = schema.research_problem
    record.method = schema.method
    record.method_category = schema.method_category
    record.datasets = schema.datasets
    record.metrics = schema.metrics
    record.main_results = schema.main_results
    record.strengths = schema.strengths
    record.limitations = schema.limitations
    record.future_work = schema.future_work
    record.keywords = schema.keywords
    record.needs_review = schema.needs_review
    record.warnings = schema.warnings
    db.commit()
    db.refresh(record)
    update_paper_metadata(db, schema.paper_id, title=schema.title, year=schema.year)
    return record


def update_schema_field_value(db: Session, paper_id: str, field_name: str, value, mark_review: bool = False) -> PaperSchemaRecord | None:
    """Update a single field inside the structured schema record."""

    record = db.get(PaperSchemaRecord, paper_id)
    if record is None:
        return None
    setattr(record, field_name, _coerce_schema_field(field_name, value))
    if mark_review:
        record.needs_review = True
    db.commit()
    db.refresh(record)
    return record


def list_project_schemas(db: Session, project_id: str) -> list[PaperSchema]:
    """List structured paper cards for a project."""

    papers = list_project_papers(db, project_id)
    schemas: list[PaperSchema] = []
    for paper in papers:
        if paper.schema_record is None:
            fallback_title = paper.title or paper.file_path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
            schemas.append(
                PaperSchema(
                    paper_id=paper.id,
                    title=fallback_title,
                    year=paper.year or extract_year(fallback_title),
                    needs_review=True,
                    warnings=["Paper has not been analyzed yet."],
                )
            )
            continue
        schemas.append(_schema_record_to_model(paper.schema_record))
    return schemas


def create_task(db: Session, project_id: str) -> Task:
    """Create a workflow task."""

    task = Task(id=f"task_{uuid.uuid4().hex[:8]}", project_id=project_id, logs=[])
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: str) -> Task | None:
    """Fetch a task by id."""

    return db.get(Task, task_id)


def update_task(
    db: Session,
    task_id: str,
    *,
    status: str | None = None,
    current_step: str | None = None,
    progress: int | None = None,
    logs: list[str] | None = None,
) -> Task | None:
    """Update a workflow task."""

    task = get_task(db, task_id)
    if task is None:
        return None
    if status is not None:
        task.status = status
    if current_step is not None:
        task.current_step = current_step
    if progress is not None:
        task.progress = progress
    if logs is not None:
        task.logs = logs
    db.commit()
    db.refresh(task)
    return task


def replace_enrichments(db: Session, evidences: list[EnrichmentEvidence]) -> None:
    """Replace enrichment evidence for the involved papers."""

    paper_ids = list({item.paper_id for item in evidences})
    if paper_ids:
        db.query(EnrichmentRecord).filter(EnrichmentRecord.paper_id.in_(paper_ids)).delete()
    for evidence in evidences:
        db.add(
            EnrichmentRecord(
                id=f"enrich_{uuid.uuid4().hex[:8]}",
                paper_id=evidence.paper_id,
                source_type=evidence.source_type,
                url=evidence.url,
                used_for_field=evidence.used_for_field,
                extracted_info=evidence.extracted_info,
            )
        )
    db.commit()


def _field_completion_record_to_model(record: FieldCompletionRecord) -> FieldCompletionResult:
    evidence = [EvidenceSnippet.model_validate(item) for item in (record.candidate_evidence or [])]
    return FieldCompletionResult(
        paper_id=record.paper_id,
        field_name=record.field_name,
        original_value=record.original_value or [],
        filled_value=record.filled_value or [],
        need_fill=record.need_fill,
        retrieval_query=record.retrieval_query,
        candidate_evidence=evidence,
        retry_count=record.retry_count,
        fill_status=record.fill_status,
        requires_human_review=record.requires_human_review,
        review_status=record.review_status,
        logs=record.logs or [],
    )


def upsert_field_completion_result(db: Session, project_id: str, result: FieldCompletionResult) -> FieldCompletionRecord:
    """Insert or update a field completion result."""

    record_id = f"{result.paper_id}:{result.field_name}"
    record = db.get(FieldCompletionRecord, record_id)
    if record is None:
        record = FieldCompletionRecord(id=record_id, project_id=project_id, paper_id=result.paper_id, field_name=result.field_name)
        db.add(record)

    record.original_value = result.original_value
    record.filled_value = result.filled_value
    record.need_fill = result.need_fill
    record.retrieval_query = result.retrieval_query
    record.candidate_evidence = [item.model_dump() for item in result.candidate_evidence]
    record.retry_count = result.retry_count
    record.fill_status = result.fill_status
    record.requires_human_review = result.requires_human_review
    record.review_status = result.review_status
    record.logs = result.logs
    db.commit()
    db.refresh(record)
    return record


def list_project_field_completions(db: Session, project_id: str) -> list[FieldCompletionResult]:
    """List all field completion results for a project."""

    stmt = select(FieldCompletionRecord).where(FieldCompletionRecord.project_id == project_id).order_by(FieldCompletionRecord.paper_id)
    return [_field_completion_record_to_model(record) for record in db.scalars(stmt)]


def list_paper_field_completions(db: Session, project_id: str, paper_id: str) -> list[FieldCompletionResult]:
    """List field completion results for a specific paper."""

    stmt = select(FieldCompletionRecord).where(
        FieldCompletionRecord.project_id == project_id,
        FieldCompletionRecord.paper_id == paper_id,
    ).order_by(FieldCompletionRecord.field_name)
    return [_field_completion_record_to_model(record) for record in db.scalars(stmt)]


def get_field_completion(db: Session, project_id: str, paper_id: str, field_name: str) -> FieldCompletionResult | None:
    """Fetch one field completion result."""

    record = db.get(FieldCompletionRecord, f"{paper_id}:{field_name}")
    if record is None or record.project_id != project_id:
        return None
    return _field_completion_record_to_model(record)


def review_field_completion(
    db: Session,
    project_id: str,
    request: FieldCompletionReviewRequest,
) -> FieldCompletionResult | None:
    """Apply a review action to a field completion result and sync the schema."""

    record = db.get(FieldCompletionRecord, f"{request.paper_id}:{request.field_name}")
    if record is None or record.project_id != project_id:
        return None

    final_value = record.filled_value
    if request.action == "approve":
        record.review_status = "approved"
    elif request.action == "reject":
        record.review_status = "rejected"
        final_value = record.original_value
    elif request.action == "edit":
        record.review_status = "approved"
        final_value = request.edited_value if request.edited_value is not None else record.filled_value
        record.filled_value = final_value

    update_schema_field_value(db, request.paper_id, request.field_name, final_value, mark_review=False)
    db.commit()
    db.refresh(record)
    return _field_completion_record_to_model(record)


def _gap_record_to_model(record: GapCandidateRecord) -> GapCandidate:
    return GapCandidate(
        gap_id=record.id,
        project_id=record.project_id,
        statement=record.statement,
        supporting_papers=record.supporting_papers or [],
        evidence_summary=record.evidence_summary or [],
        supporting_evidence=[EvidenceSnippet.model_validate(item) for item in (record.supporting_evidence or [])],
        counter_evidence=[EvidenceSnippet.model_validate(item) for item in (record.counter_evidence or [])],
        coverage_count=record.coverage_count,
        validation_result=record.validation_result,
        confidence=record.confidence,
        suggested_direction=record.suggested_direction,
        requires_human_review=record.requires_human_review,
        status=record.status,
    )


def list_project_gaps(db: Session, project_id: str) -> list[GapCandidate]:
    """List gap candidates for a project."""

    stmt = select(GapCandidateRecord).where(GapCandidateRecord.project_id == project_id).order_by(GapCandidateRecord.id)
    return [_gap_record_to_model(record) for record in db.scalars(stmt)]


def get_gap_candidate(db: Session, project_id: str, gap_id: str) -> GapCandidate | None:
    """Fetch one gap candidate."""

    record = db.get(GapCandidateRecord, gap_id)
    if record is None or record.project_id != project_id:
        return None
    return _gap_record_to_model(record)


def replace_gap_candidates(db: Session, project_id: str, candidates: list[GapCandidate]) -> None:
    """Replace all gap candidates for a project."""

    db.query(GapCandidateRecord).filter(GapCandidateRecord.project_id == project_id).delete()
    for candidate in candidates:
        db.add(
            GapCandidateRecord(
                id=candidate.gap_id,
                project_id=project_id,
                statement=candidate.statement,
                supporting_papers=candidate.supporting_papers,
                evidence_summary=candidate.evidence_summary,
                supporting_evidence=[item.model_dump() for item in candidate.supporting_evidence],
                counter_evidence=[item.model_dump() for item in candidate.counter_evidence],
                coverage_count=candidate.coverage_count,
                validation_result=candidate.validation_result,
                confidence=candidate.confidence,
                suggested_direction=candidate.suggested_direction,
                requires_human_review=candidate.requires_human_review,
                status=candidate.status,
            )
        )
    db.commit()


def review_gap_candidate(db: Session, project_id: str, request: GapReviewRequest) -> GapCandidate | None:
    """Apply a review action to a gap candidate."""

    record = db.get(GapCandidateRecord, request.gap_id)
    if record is None or record.project_id != project_id:
        return None

    if request.action == "approve":
        record.status = "approved"
    elif request.action == "reject":
        record.status = "rejected"
    elif request.action == "edit":
        record.status = "approved"
        if request.edited_statement:
            record.statement = request.edited_statement
        if request.edited_suggested_direction:
            record.suggested_direction = request.edited_suggested_direction

    db.commit()
    db.refresh(record)
    return _gap_record_to_model(record)
