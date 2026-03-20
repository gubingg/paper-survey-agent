from __future__ import annotations

import traceback

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import crud
from app.db.session import get_db
from app.graph.workflow import run_workflow
from app.schemas.api_schema import (
    AnalyzeProjectRequest,
    AnalyzeProjectResponse,
    CompareResponse,
    TaskResponse,
)
from app.schemas.graph_state import MainWorkflowState
from app.services.compare_service import CompareService

router = APIRouter(tags=["analysis"])
compare_service = CompareService()


@router.post("/api/projects/{project_id}/analyze", response_model=AnalyzeProjectResponse)
def analyze_project(
    project_id: str,
    payload: AnalyzeProjectRequest,
    db: Session = Depends(get_db),
) -> AnalyzeProjectResponse:
    """Run the analysis workflow synchronously."""

    project = crud.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    papers = crud.list_project_papers(db, project_id)
    if not papers:
        raise HTTPException(status_code=400, detail="Please upload at least one PDF before analysis.")

    task = crud.create_task(db, project_id)
    crud.update_task(db, task.id, status="running", current_step="workflow", progress=10, logs=["Workflow started."])

    try:
        initial_state = MainWorkflowState(
            project_id=project.id,
            topic=project.topic,
            target_type=project.target_type,
            paper_ids=[paper.id for paper in papers],
            enable_gap_analysis=payload.enable_gap_analysis,
            enable_external_search=payload.enable_external_search,
        )
        final_state = run_workflow(initial_state)
        crud.update_task(
            db,
            task.id,
            status="completed",
            current_step="done",
            progress=100,
            logs=final_state.logs,
        )
        return AnalyzeProjectResponse(task_id=task.id, status="completed")
    except Exception as exc:
        error_logs = [str(exc), traceback.format_exc()]
        crud.update_task(db, task.id, status="failed", current_step="error", progress=100, logs=error_logs)
        raise HTTPException(status_code=500, detail=f"Analysis workflow failed: {exc}") from exc


@router.get("/api/tasks/{task_id}", response_model=TaskResponse)
def get_task_status(task_id: str, db: Session = Depends(get_db)) -> TaskResponse:
    """Return task progress information."""

    task = crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return TaskResponse(
        task_id=task.id,
        project_id=task.project_id,
        status=task.status,
        current_step=task.current_step,
        progress=task.progress,
        logs=task.logs or [],
    )


@router.get("/api/projects/{project_id}/compare", response_model=CompareResponse)
def get_compare_result(project_id: str, db: Session = Depends(get_db)) -> CompareResponse:
    """Return the current project comparison result."""

    project = crud.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    try:
        paper_schemas = crud.list_project_schemas(db, project_id)
        compare_result = compare_service.build_compare_result(paper_schemas, topic=project.topic)
        return CompareResponse(project_id=project_id, compare_result=compare_result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to build compare result: {exc}") from exc
