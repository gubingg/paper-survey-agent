from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.agent_schema import FieldCompletionResult, FieldCompletionReviewRequest, FieldCompletionReviewResponse
from app.schemas.gap_schema import GapCandidate, GapReviewRequest
from app.schemas.paper_schema import CompareResult, ExportPayload, PaperSchema


TargetType = Literal["survey", "meeting_outline", "gap_analysis"]
ExportType = Literal["survey", "meeting_outline", "gap_analysis", "compare_table", "related_work_markdown"]


class CreateProjectRequest(BaseModel):
    """Request body for project creation."""

    project_name: str
    topic: str
    target_type: TargetType = "meeting_outline"


class CreateProjectResponse(BaseModel):
    """Response after a project is created."""

    project_id: str


class UploadPapersResponse(BaseModel):
    """Response after PDFs are uploaded."""

    paper_ids: list[str] = Field(default_factory=list)
    file_paths: list[str] = Field(default_factory=list)


class AnalyzeProjectRequest(BaseModel):
    """Request body for analysis workflow execution."""

    enable_gap_analysis: bool = True
    enable_external_search: bool = False


class AnalyzeProjectResponse(BaseModel):
    """Response after an analysis task is created."""

    task_id: str
    status: str


class TaskResponse(BaseModel):
    """Task status response."""

    task_id: str
    project_id: str
    status: str
    current_step: str
    progress: int
    logs: list[str] = Field(default_factory=list)


class PaperListResponse(BaseModel):
    """Project-level paper cards."""

    papers: list[PaperSchema] = Field(default_factory=list)


class TranslateProjectResponse(BaseModel):
    """Response after translating one project's results."""

    project_id: str
    translated_papers: list[PaperSchema] = Field(default_factory=list)


class CompareResponse(BaseModel):
    """Project-level comparison response."""

    project_id: str
    compare_result: CompareResult


class GapListResponse(BaseModel):
    """Project-level gap response."""

    project_id: str
    gaps: list[GapCandidate] = Field(default_factory=list)


class GapReviewResponse(BaseModel):
    """Response after gap review."""

    gap: GapCandidate


class FieldCompletionListResponse(BaseModel):
    """Project-level field completion results."""

    project_id: str
    field_completions: list[FieldCompletionResult] = Field(default_factory=list)


class FieldCompletionDetailResponse(BaseModel):
    """Paper-level field completion results."""

    project_id: str
    paper_id: str
    field_completions: list[FieldCompletionResult] = Field(default_factory=list)


class GapEvidenceResponse(BaseModel):
    """Gap evidence response."""

    gap: GapCandidate


class ExportRequest(BaseModel):
    """Export request body."""

    export_type: ExportType = "meeting_outline"


class ExportResponse(BaseModel):
    """Export response with saved file path."""

    export: ExportPayload


class ErrorResponse(BaseModel):
    """Fallback error response model."""

    detail: str
