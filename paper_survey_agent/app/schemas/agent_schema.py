from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceSnippet(BaseModel):
    """Evidence snippet retrieved from internal paper chunks."""

    paper_id: str
    chunk_id: str = ""
    section: str = "unknown"
    page_start: int = 0
    page_end: int = 0
    content: str
    score: float = 0.0


class FieldProblem(BaseModel):
    """A suspicious or incomplete field detected after extraction."""

    paper_id: str
    field_name: Literal["datasets", "metrics", "limitations", "future_work"]
    current_value: str | list[str] = Field(default_factory=list)
    reason: str
    severity: Literal["low", "medium", "high"] = "medium"


class FieldCompletionResult(BaseModel):
    """Final result of the field completion agent for one field."""

    paper_id: str
    field_name: str
    original_value: str | list[str] = Field(default_factory=list)
    filled_value: str | list[str] = Field(default_factory=list)
    need_fill: bool = False
    retrieval_query: str = ""
    candidate_evidence: list[EvidenceSnippet] = Field(default_factory=list)
    retry_count: int = 0
    fill_status: Literal["filled", "evidence_insufficient", "not_needed", "not_mentioned"] = "not_needed"
    requires_human_review: bool = False
    review_status: Literal["pending", "approved", "rejected"] = "pending"
    logs: list[str] = Field(default_factory=list)


class FieldCompletionReviewRequest(BaseModel):
    """Review request for a field completion result."""

    paper_id: str
    field_name: str
    action: Literal["approve", "reject", "edit"]
    edited_value: str | list[str] | None = None


class FieldCompletionReviewResponse(BaseModel):
    """Response for a field completion review action."""

    result: FieldCompletionResult


class GapValidationSummary(BaseModel):
    """Compact validation output used in gap candidates and exports."""

    validation_result: Literal["成立", "证据弱", "有冲突", "不成立"] | None = None
    confidence: float = 0.0
    coverage_count: int = 0
    requires_human_review: bool = False


class AgentLogResponse(BaseModel):
    """Reusable response wrapper for agent outputs."""

    items: list[Any] = Field(default_factory=list)
