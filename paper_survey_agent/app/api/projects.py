from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import crud
from app.db.session import get_db
from app.schemas.api_schema import CreateProjectRequest, CreateProjectResponse

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=CreateProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: CreateProjectRequest, db: Session = Depends(get_db)) -> CreateProjectResponse:
    """Create a new paper survey project."""

    try:
        project = crud.create_project(db, payload.project_name, payload.topic, payload.target_type)
        return CreateProjectResponse(project_id=project.id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {exc}") from exc
