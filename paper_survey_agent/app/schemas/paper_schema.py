from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PageBlock(BaseModel):
    """A positioned text block extracted from a PDF page."""

    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    block_no: int


class ParsedPage(BaseModel):
    """Single-page parsed content with raw text and blocks."""

    page: int
    text: str = ""
    blocks: list[PageBlock] = Field(default_factory=list)


class PaperChunk(BaseModel):
    """Chunked content that can be used for extraction or retrieval."""

    chunk_id: str
    paper_id: str
    section: str = "unknown"
    page_start: int
    page_end: int
    content: str


class ParsedPaper(BaseModel):
    """Parsed paper content persisted after PDF processing."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    paper_id: str
    title_guess: str = ""
    pages: list[ParsedPage] = Field(default_factory=list)
    full_text: str = ""
    chunks: list[PaperChunk] = Field(default_factory=list)


class PaperSchema(BaseModel):
    """Normalized paper card shared across the whole workflow."""

    paper_id: str
    title: str
    year: int | None = None
    research_problem: str = ""
    method: str = ""
    method_category: str | None = None
    datasets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    main_results: str = ""
    strengths: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    future_work: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    needs_review: bool = False
    warnings: list[str] = Field(default_factory=list)


class CompareMatrixRow(BaseModel):
    """One row in the cross-paper comparison table."""

    paper_id: str
    title: str
    research_problem: str
    method: str
    datasets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class CompareResult(BaseModel):
    """Comparison table plus short trend summary for the project."""

    rows: list[CompareMatrixRow] = Field(default_factory=list)
    trend_summary: str = ""
    method_categories: list[str] = Field(default_factory=list)
    dataset_trends: list[str] = Field(default_factory=list)
    metric_trends: list[str] = Field(default_factory=list)


class ExportPayload(BaseModel):
    """Structured export result returned by the export service."""

    export_type: Literal["survey", "meeting_outline", "gap_analysis", "compare_table", "related_work_markdown"]
    content: str
    file_path: str
