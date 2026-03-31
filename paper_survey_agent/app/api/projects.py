from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import crud
from app.db.session import get_db
from app.schemas.api_schema import (
    CreateProjectRequest,
    CreateProjectResponse,
    DeleteProjectResponse,
    ProjectListResponse,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])
project_service = ProjectService()


@router.get("", response_model=ProjectListResponse)
def list_projects(db: Session = Depends(get_db)) -> ProjectListResponse:
    """List all projects for the frontend project switcher."""

    try:
        return project_service.list_projects(db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {exc}") from exc


@router.post("", response_model=CreateProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: CreateProjectRequest, db: Session = Depends(get_db)) -> CreateProjectResponse:
    """Create a new paper survey project."""

    try:
        project = crud.create_project(
            db,
            payload.project_name,
            payload.topic,
            payload.target_type,
            focus_dimensions=payload.focus_dimensions,
            user_requirements=payload.user_requirements,
            gap_validation_level=payload.gap_validation_level,
        )
        return CreateProjectResponse(project_id=project.id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {exc}") from exc


@router.delete("/{project_id}", response_model=DeleteProjectResponse)
def delete_project(project_id: str, db: Session = Depends(get_db)) -> DeleteProjectResponse:
    """Delete one project and reclaim orphaned paper/vector assets."""

    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        return project_service.delete_project(db, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {exc}") from exc
