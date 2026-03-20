from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.agent_schema import EvidenceSnippet


class MissingFieldResult(BaseModel):
    """Missing field detection result for one paper."""

    paper_id: str
    missing_fields: list[str] = Field(default_factory=list)
    need_enrichment: bool = False


class EnrichmentEvidence(BaseModel):
    """Reserved external evidence model for future use."""

    paper_id: str
    source_type: str
    url: str
    used_for_field: str
    extracted_info: str


class GapCandidate(BaseModel):
    """Research gap candidate and its validation result."""

    gap_id: str
    project_id: str
    statement: str
    supporting_papers: list[str] = Field(default_factory=list)
    evidence_summary: list[str] = Field(default_factory=list)
    supporting_evidence: list[EvidenceSnippet] = Field(default_factory=list)
    counter_evidence: list[EvidenceSnippet] = Field(default_factory=list)
    coverage_count: int = 0
    validation_result: Literal["成立", "证据弱", "有冲突", "不成立"] | None = None
    confidence: float = 0.0
    suggested_direction: str = ""
    requires_human_review: bool = False
    status: Literal["pending", "approved", "rejected"] = "pending"


class GapReviewRequest(BaseModel):
    """Review request from the frontend."""

    gap_id: str
    action: Literal["approve", "reject", "edit"]
    edited_statement: str | None = None
    edited_suggested_direction: str | None = None
