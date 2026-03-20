from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import crud
from app.db.session import get_db
from app.schemas.agent_schema import FieldCompletionReviewRequest, FieldCompletionReviewResponse
from app.schemas.api_schema import (
    FieldCompletionDetailResponse,
    FieldCompletionListResponse,
    PaperListResponse,
    TranslateProjectResponse,
    UploadPapersResponse,
)
from app.services.translation_service import TranslationService
from app.utils.file_utils import save_upload_file

router = APIRouter(tags=["papers"])
translation_service = TranslationService()


@router.post("/api/projects/{project_id}/papers/upload", response_model=UploadPapersResponse)
def upload_papers(
    project_id: str,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> UploadPapersResponse:
    """Upload multiple paper PDFs into a project."""

    project = crud.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    paper_ids: list[str] = []
    file_paths: list[str] = []
    try:
        for upload in files:
            if Path(upload.filename).suffix.lower() != ".pdf":
                raise HTTPException(status_code=400, detail=f"Only PDF files are allowed: {upload.filename}")
            file_path = save_upload_file(project_id, upload)
            paper = crud.create_paper(db, project_id=project_id, file_path=file_path, title=Path(upload.filename).stem)
            paper_ids.append(paper.id)
            file_paths.append(file_path)
        return UploadPapersResponse(paper_ids=paper_ids, file_paths=file_paths)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to upload papers: {exc}") from exc


@router.get("/api/projects/{project_id}/papers", response_model=PaperListResponse)
def get_project_papers(project_id: str, db: Session = Depends(get_db)) -> PaperListResponse:
    """Return structured paper cards for the project."""

    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        return PaperListResponse(papers=crud.list_project_schemas(db, project_id))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch papers: {exc}") from exc


@router.post("/api/projects/{project_id}/translate-results", response_model=TranslateProjectResponse)
def translate_project_results(project_id: str, db: Session = Depends(get_db)) -> TranslateProjectResponse:
    """Translate one project's stored paper cards on demand."""

    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        schemas = crud.list_project_schemas(db, project_id)
        translated = translation_service.localize_schemas(schemas)
        for schema in translated:
            crud.upsert_paper_schema(db, schema)
        return TranslateProjectResponse(project_id=project_id, translated_papers=translated)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to translate project results: {exc}") from exc


@router.get("/api/projects/{project_id}/field-completions", response_model=FieldCompletionListResponse)
def get_project_field_completions(project_id: str, db: Session = Depends(get_db)) -> FieldCompletionListResponse:
    """Return field completion logs and evidence for a project."""

    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        return FieldCompletionListResponse(
            project_id=project_id,
            field_completions=crud.list_project_field_completions(db, project_id),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch field completion results: {exc}") from exc


@router.get("/api/projects/{project_id}/papers/{paper_id}/field-completions", response_model=FieldCompletionDetailResponse)
def get_paper_field_completions(project_id: str, paper_id: str, db: Session = Depends(get_db)) -> FieldCompletionDetailResponse:
    """Return field completion details for a specific paper."""

    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        return FieldCompletionDetailResponse(
            project_id=project_id,
            paper_id=paper_id,
            field_completions=crud.list_paper_field_completions(db, project_id, paper_id),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch field completion details: {exc}") from exc


@router.post("/api/projects/{project_id}/field-completions/review", response_model=FieldCompletionReviewResponse)
def review_field_completion(
    project_id: str,
    payload: FieldCompletionReviewRequest,
    db: Session = Depends(get_db),
) -> FieldCompletionReviewResponse:
    """Review a field completion result."""

    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        result = crud.review_field_completion(db, project_id, payload)
        if result is None:
            raise HTTPException(status_code=404, detail="Field completion result not found.")
        return FieldCompletionReviewResponse(result=result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to review field completion result: {exc}") from exc
