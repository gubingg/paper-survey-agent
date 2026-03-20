from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.agent_schema import EvidenceSnippet, FieldCompletionResult, FieldProblem
from app.schemas.gap_schema import GapCandidate
from app.schemas.paper_schema import CompareResult, PaperChunk, ParsedPaper, PaperSchema


class MainWorkflowState(BaseModel):
    """State shared by the main workflow."""

    project_id: str
    topic: str = ""
    target_type: str = "meeting_outline"
    paper_ids: list[str] = Field(default_factory=list)
    parsed_papers: list[ParsedPaper] = Field(default_factory=list)
    paper_schemas: list[PaperSchema] = Field(default_factory=list)
    problem_fields: list[FieldProblem] = Field(default_factory=list)
    field_completion_results: list[FieldCompletionResult] = Field(default_factory=list)
    compare_result: CompareResult | None = None
    gap_candidates: list[GapCandidate] = Field(default_factory=list)
    approved_gaps: list[GapCandidate] = Field(default_factory=list)
    export_payload: dict | None = None
    logs: list[str] = Field(default_factory=list)
    enable_gap_analysis: bool = True
    enable_external_search: bool = False


class FieldCompletionAgentState(BaseModel):
    """State used inside the field completion subgraph."""

    project_id: str
    paper_id: str
    field_name: str
    current_value: str | list[str] = Field(default_factory=list)
    need_fill: bool = False
    problem_reason: str = ""
    retrieval_query: str = ""
    candidate_evidence: list[EvidenceSnippet] = Field(default_factory=list)
    evidence_sufficient: bool = False
    retry_count: int = 0
    filled_value: str | list[str] = Field(default_factory=list)
    fill_status: str = "not_needed"
    requires_human_review: bool = False
    chunks: list[PaperChunk] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)


class GapValidationAgentState(BaseModel):
    """State used inside the gap validation subgraph."""

    project_id: str
    gap_id: str
    gap_statement: str
    supporting_evidence: list[EvidenceSnippet] = Field(default_factory=list)
    counter_evidence: list[EvidenceSnippet] = Field(default_factory=list)
    coverage_count: int = 0
    retry_count: int = 0
    validation_result: str | None = None
    confidence: float = 0.0
    requires_human_review: bool = False
    evidence_sufficient: bool = False
    candidate: GapCandidate | None = None
    compare_result: CompareResult | None = None
    paper_schemas: list[PaperSchema] = Field(default_factory=list)
    chunks: list[PaperChunk] = Field(default_factory=list)
    verification_points: list[str] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
