from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import crud
from app.db.session import get_db
from app.schemas.api_schema import ExportRequest, ExportResponse
from app.services.compare_service import CompareService
from app.services.export_service import ExportService

router = APIRouter(tags=["export"])
compare_service = CompareService()
export_service = ExportService()


@router.post("/api/projects/{project_id}/export", response_model=ExportResponse)
def export_project(
    project_id: str,
    payload: ExportRequest,
    db: Session = Depends(get_db),
) -> ExportResponse:
    """Export survey, meeting outline, gap analysis, or compare table."""

    project = crud.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    try:
        paper_schemas = crud.list_project_schemas(db, project_id)
        compare_result = compare_service.build_compare_result(
            paper_schemas,
            topic=project.topic,
            focus_dimensions=project.focus_dimensions or [],
            user_requirements=project.user_requirements or "",
        )
        gaps = crud.list_project_gaps(db, project_id)
        export_payload = export_service.export(
            project_id=project_id,
            export_type=payload.export_type,
            topic=project.topic,
            paper_schemas=paper_schemas,
            compare_result=compare_result,
            gap_candidates=gaps,
            focus_dimensions=project.focus_dimensions or [],
            user_requirements=project.user_requirements or "",
        )
        return ExportResponse(export=export_payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to export project result: {exc}") from exc
