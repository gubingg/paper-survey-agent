from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import crud
from app.db.session import get_db
from app.schemas.api_schema import GapEvidenceResponse, GapListResponse, GapReviewResponse
from app.schemas.gap_schema import GapReviewRequest

router = APIRouter(tags=["gaps"])


@router.get("/api/projects/{project_id}/gaps", response_model=GapListResponse)
def get_project_gaps(project_id: str, db: Session = Depends(get_db)) -> GapListResponse:
    """Return generated gap candidates for a project."""

    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        gaps = crud.list_project_gaps(db, project_id)
        return GapListResponse(project_id=project_id, gaps=gaps)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch gap candidates: {exc}") from exc


@router.get("/api/projects/{project_id}/gaps/{gap_id}/evidence", response_model=GapEvidenceResponse)
def get_gap_evidence(project_id: str, gap_id: str, db: Session = Depends(get_db)) -> GapEvidenceResponse:
    """Return support and counter evidence for a gap candidate."""

    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        gap = crud.get_gap_candidate(db, project_id, gap_id)
        if gap is None:
            raise HTTPException(status_code=404, detail="Gap candidate not found.")
        return GapEvidenceResponse(gap=gap)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch gap evidence: {exc}") from exc


@router.post("/api/projects/{project_id}/gaps/review", response_model=GapReviewResponse)
def review_gap(
    project_id: str,
    payload: GapReviewRequest,
    db: Session = Depends(get_db),
) -> GapReviewResponse:
    """Apply a manual review action to a gap candidate."""

    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        gap = crud.review_gap_candidate(db, project_id, payload)
        if gap is None:
            raise HTTPException(status_code=404, detail="Gap candidate not found.")
        return GapReviewResponse(gap=gap)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to review gap candidate: {exc}") from exc
