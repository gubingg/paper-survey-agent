from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    EnrichmentRecord,
    FieldCompletionRecord,
    GapCandidateRecord,
    Paper,
    PaperChunkRecord,
    PaperSchemaRecord,
    Project,
    ProjectPaper,
    Task,
)
from app.schemas.agent_schema import (
    EvidenceSnippet,
    FieldCompletionResult,
    FieldCompletionReviewRequest,
)
from app.schemas.api_schema import ProjectSummary
from app.schemas.gap_schema import EnrichmentEvidence, GapCandidate, GapReviewRequest
from app.schemas.paper_schema import PaperChunk, PaperSchema
from app.utils.chunk_utils import extract_year
from app.utils.gap_validation_utils import resolve_gap_validation_level


LIST_FIELDS = {"datasets", "metrics", "limitations", "future_work", "keywords", "strengths"}


def create_project(
    db: Session,
    name: str,
    topic: str,
    target_type: str,
    focus_dimensions: list[str] | None = None,
    user_requirements: str = "",
    gap_validation_level: str | None = None,
) -> Project:
    """Create a project record."""

    project = Project(
        id=f"proj_{uuid.uuid4().hex[:8]}",
        name=name,
        topic=topic,
        target_type=target_type,
        focus_dimensions=focus_dimensions or [],
        user_requirements=user_requirements,
        gap_validation_level=resolve_gap_validation_level(target_type, gap_validation_level),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def list_projects(db: Session) -> list[ProjectSummary]:
    """List all projects with paper counts."""

    stmt = (
        select(Project, func.count(ProjectPaper.paper_id))
        .outerjoin(ProjectPaper, ProjectPaper.project_id == Project.id)
        .group_by(Project.id)
        .order_by(Project.created_at.desc())
    )
    summaries: list[ProjectSummary] = []
    for project, paper_count in db.execute(stmt).all():
        summaries.append(
            ProjectSummary(
                project_id=project.id,
                project_name=project.name,
                topic=project.topic,
                target_type=project.target_type,
                focus_dimensions=project.focus_dimensions or [],
                user_requirements=project.user_requirements or "",
                gap_validation_level=resolve_gap_validation_level(project.target_type, project.gap_validation_level),
                created_at=project.created_at,
                paper_count=int(paper_count or 0),
            )
        )
    return summaries


def get_project(db: Session, project_id: str) -> Project | None:
    """Fetch a project by id."""

    return db.get(Project, project_id)


def get_paper(db: Session, paper_id: str) -> Paper | None:
    """Fetch a paper by id."""

    return db.get(Paper, paper_id)


def get_paper_by_hash(db: Session, file_hash: str) -> Paper | None:
    """Fetch a globally stored paper by sha256 hash."""

    if not file_hash:
        return None
    stmt = select(Paper).where(Paper.file_hash == file_hash)
    return db.scalar(stmt)


def link_paper_to_project(db: Session, project_id: str, paper_id: str) -> bool:
    """Create a project-paper link if it does not already exist."""

    link = db.get(ProjectPaper, {"project_id": project_id, "paper_id": paper_id})
    if link is not None:
        return False
    db.add(ProjectPaper(project_id=project_id, paper_id=paper_id))
    return True


def create_or_link_paper(
    db: Session,
    project_id: str,
    *,
    file_path: str,
    file_hash: str,
    title: str = "",
    original_filename: str = "",
) -> tuple[Paper, bool, bool]:
    """Create one global paper or reuse it, then link it to the project."""

    paper = get_paper_by_hash(db, file_hash)
    created_new = False
    if paper is None:
        paper = Paper(
            id=f"paper_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            file_path=file_path,
            file_hash=file_hash,
            original_filename=original_filename,
            title=title,
        )
        db.add(paper)
        db.flush()
        created_new = True
    else:
        if not paper.original_filename and original_filename:
            paper.original_filename = original_filename
        if title and not paper.title:
            paper.title = title
        if not paper.project_id:
            paper.project_id = project_id

    linked_new = link_paper_to_project(db, project_id, paper.id)
    db.commit()
    db.refresh(paper)
    return paper, created_new, linked_new


def list_project_papers(db: Session, project_id: str) -> list[Paper]:
    """List all globally stored papers linked to one project."""

    stmt = (
        select(Paper)
        .join(ProjectPaper, ProjectPaper.paper_id == Paper.id)
        .where(ProjectPaper.project_id == project_id)
        .order_by(Paper.id)
    )
    papers = list(db.scalars(stmt))
    if papers:
        return papers

    legacy_stmt = select(Paper).where(Paper.project_id == project_id).order_by(Paper.id)
    return list(db.scalars(legacy_stmt))


def list_project_paper_ids(db: Session, project_id: str) -> list[str]:
    """Return linked paper ids for one project."""

    stmt = select(ProjectPaper.paper_id).where(ProjectPaper.project_id == project_id)
    paper_ids = list(db.scalars(stmt))
    if paper_ids:
        return paper_ids
    legacy_stmt = select(Paper.id).where(Paper.project_id == project_id)
    return list(db.scalars(legacy_stmt))


def list_other_project_ids_for_paper(db: Session, paper_id: str, *, excluding_project_id: str | None = None) -> list[str]:
    """List other projects that still reference one paper."""

    stmt = select(ProjectPaper.project_id).where(ProjectPaper.paper_id == paper_id)
    if excluding_project_id:
        stmt = stmt.where(ProjectPaper.project_id != excluding_project_id)
    return list(db.scalars(stmt))


def update_paper_owner_project(db: Session, paper_id: str, owner_project_id: str | None) -> None:
    """Update the owner-project pointer kept for compatibility."""

    paper = get_paper(db, paper_id)
    if paper is None:
        return
    paper.project_id = owner_project_id
    db.commit()


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

    paper_ids = list_project_paper_ids(db, project_id)
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
        return " | ".join(str(item) for item in value if str(item).strip())
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
            fallback_title = paper.title or paper.original_filename or paper.file_path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
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

    record_id = f"{project_id}:{result.paper_id}:{result.field_name}"
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

    record = db.get(FieldCompletionRecord, f"{project_id}:{paper_id}:{field_name}")
    if record is None or record.project_id != project_id:
        return None
    return _field_completion_record_to_model(record)


def review_field_completion(
    db: Session,
    project_id: str,
    request: FieldCompletionReviewRequest,
) -> FieldCompletionResult | None:
    """Apply a review action to a field completion result and sync the schema."""

    record = db.get(FieldCompletionRecord, f"{project_id}:{request.paper_id}:{request.field_name}")
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
        original_statement=record.original_statement or record.statement,
        statement=record.statement,
        source_context=record.source_context or "",
        supporting_papers=record.supporting_papers or [],
        evidence_summary=record.evidence_summary or [],
        supporting_evidence=[EvidenceSnippet.model_validate(item) for item in (record.supporting_evidence or [])],
        counter_evidence=[EvidenceSnippet.model_validate(item) for item in (record.counter_evidence or [])],
        coverage_count=record.coverage_count,
        validation_result=record.validation_result,
        validation_level=record.validation_level or "raw",
        confidence=record.confidence,
        suggested_direction=record.suggested_direction,
        validation_reason=record.validation_reason or "",
        normalized_gap=record.normalized_gap or {},
        support_strength=record.support_strength or "",
        support_reason=record.support_reason or "",
        support_count=record.support_count or 0,
        distinct_paper_count=record.distinct_paper_count or 0,
        counter_strength=record.counter_strength or "",
        counter_reason=record.counter_reason or "",
        coverage_status=record.coverage_status or "",
        coverage_reason=record.coverage_reason or "",
        coverage_risks=record.coverage_risks or [],
        external_search_used=record.external_search_used,
        requires_human_review=record.requires_human_review,
        human_review_reason=record.human_review_reason or "",
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
                original_statement=candidate.original_statement or candidate.statement,
                statement=candidate.statement,
                source_context=candidate.source_context,
                supporting_papers=candidate.supporting_papers,
                evidence_summary=candidate.evidence_summary,
                supporting_evidence=[item.model_dump() for item in candidate.supporting_evidence],
                counter_evidence=[item.model_dump() for item in candidate.counter_evidence],
                coverage_count=candidate.coverage_count,
                validation_result=candidate.validation_result,
                validation_level=candidate.validation_level,
                confidence=candidate.confidence,
                suggested_direction=candidate.suggested_direction,
                validation_reason=candidate.validation_reason,
                normalized_gap=candidate.normalized_gap,
                support_strength=candidate.support_strength,
                support_reason=candidate.support_reason,
                support_count=candidate.support_count,
                distinct_paper_count=candidate.distinct_paper_count,
                counter_strength=candidate.counter_strength,
                counter_reason=candidate.counter_reason,
                coverage_status=candidate.coverage_status,
                coverage_reason=candidate.coverage_reason,
                coverage_risks=candidate.coverage_risks,
                external_search_used=candidate.external_search_used,
                requires_human_review=candidate.requires_human_review,
                human_review_reason=candidate.human_review_reason,
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


def delete_project_records(db: Session, project_id: str) -> None:
    """Delete project-local records while leaving shared paper assets intact."""

    db.query(FieldCompletionRecord).filter(FieldCompletionRecord.project_id == project_id).delete()
    db.query(GapCandidateRecord).filter(GapCandidateRecord.project_id == project_id).delete()
    db.query(Task).filter(Task.project_id == project_id).delete()
    db.query(ProjectPaper).filter(ProjectPaper.project_id == project_id).delete()
    db.query(Project).filter(Project.id == project_id).delete()
    db.commit()


def delete_paper_asset(db: Session, paper_id: str) -> None:
    """Delete one orphaned paper and all of its persistent DB records."""

    db.query(FieldCompletionRecord).filter(FieldCompletionRecord.paper_id == paper_id).delete()
    db.query(EnrichmentRecord).filter(EnrichmentRecord.paper_id == paper_id).delete()
    db.query(PaperChunkRecord).filter(PaperChunkRecord.paper_id == paper_id).delete()
    db.query(PaperSchemaRecord).filter(PaperSchemaRecord.paper_id == paper_id).delete()
    db.query(ProjectPaper).filter(ProjectPaper.paper_id == paper_id).delete()
    db.query(Paper).filter(Paper.id == paper_id).delete()
    db.commit()



