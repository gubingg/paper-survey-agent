from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative model."""


class Project(Base):
    """Project record."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    focus_dimensions: Mapped[list] = mapped_column(JSON, default=list)
    domain_hint: Mapped[str] = mapped_column(String(128), default="")
    user_requirements: Mapped[str] = mapped_column(Text, default="")
    gap_validation_level: Mapped[str] = mapped_column(String(16), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    paper_links: Mapped[list["ProjectPaper"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    gaps: Mapped[list["GapCandidateRecord"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    field_completions: Mapped[list["FieldCompletionRecord"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Paper(Base):
    """Globally stored paper metadata."""

    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True, nullable=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    original_filename: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    project_links: Mapped[list["ProjectPaper"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    chunks: Mapped[list["PaperChunkRecord"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    schema_record: Mapped["PaperSchemaRecord | None"] = relationship(back_populates="paper", cascade="all, delete-orphan")
    enrichments: Mapped[list["EnrichmentRecord"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    field_completions: Mapped[list["FieldCompletionRecord"]] = relationship(back_populates="paper", cascade="all, delete-orphan")


class ProjectPaper(Base):
    """Many-to-many link between projects and globally stored papers."""

    __tablename__ = "project_papers"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"), primary_key=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped[Project] = relationship(back_populates="paper_links")
    paper: Mapped[Paper] = relationship(back_populates="project_links")


class PaperChunkRecord(Base):
    """Stored paper chunks."""

    __tablename__ = "paper_chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"), index=True)
    section: Mapped[str] = mapped_column(String(64), default="unknown")
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    paper: Mapped[Paper] = relationship(back_populates="chunks")


class PaperSchemaRecord(Base):
    """Structured extraction result."""

    __tablename__ = "paper_schemas"

    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"), primary_key=True)
    title: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    research_problem: Mapped[str] = mapped_column(Text, default="")
    method: Mapped[str] = mapped_column(Text, default="")
    method_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    datasets: Mapped[list] = mapped_column(JSON, default=list)
    metrics: Mapped[list] = mapped_column(JSON, default=list)
    main_results: Mapped[str] = mapped_column(Text, default="")
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    limitations: Mapped[list] = mapped_column(JSON, default=list)
    future_work: Mapped[list] = mapped_column(JSON, default=list)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    warnings: Mapped[list] = mapped_column(JSON, default=list)

    paper: Mapped[Paper] = relationship(back_populates="schema_record")


class EnrichmentRecord(Base):
    """Reserved external enrichment evidence."""

    __tablename__ = "enrichments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    used_for_field: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_info: Mapped[str] = mapped_column(Text, nullable=False)

    paper: Mapped[Paper] = relationship(back_populates="enrichments")


class FieldCompletionRecord(Base):
    """Field completion agent output for one paper field."""

    __tablename__ = "field_completion_results"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"), index=True)
    field_name: Mapped[str] = mapped_column(String(64), index=True)
    original_value: Mapped[object] = mapped_column(JSON, default=list)
    filled_value: Mapped[object] = mapped_column(JSON, default=list)
    need_fill: Mapped[bool] = mapped_column(Boolean, default=False)
    retrieval_query: Mapped[str] = mapped_column(Text, default="")
    candidate_evidence: Mapped[list] = mapped_column(JSON, default=list)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    fill_status: Mapped[str] = mapped_column(String(64), default="not_needed")
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[str] = mapped_column(String(32), default="pending")
    logs: Mapped[list] = mapped_column(JSON, default=list)

    project: Mapped[Project] = relationship(back_populates="field_completions")
    paper: Mapped[Paper] = relationship(back_populates="field_completions")


class GapCandidateRecord(Base):
    """Research gap candidate plus validation details."""

    __tablename__ = "gap_candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    original_statement: Mapped[str] = mapped_column(Text, default="")
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    source_context: Mapped[str] = mapped_column(Text, default="")
    supporting_papers: Mapped[list] = mapped_column(JSON, default=list)
    evidence_summary: Mapped[list] = mapped_column(JSON, default=list)
    supporting_evidence: Mapped[list] = mapped_column(JSON, default=list)
    counter_evidence: Mapped[list] = mapped_column(JSON, default=list)
    coverage_count: Mapped[int] = mapped_column(Integer, default=0)
    validation_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    validation_level: Mapped[str] = mapped_column(String(16), default="raw")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    suggested_direction: Mapped[str] = mapped_column(Text, default="")
    validation_reason: Mapped[str] = mapped_column(Text, default="")
    normalized_gap: Mapped[dict] = mapped_column(JSON, default=dict)
    support_strength: Mapped[str] = mapped_column(String(16), default="")
    support_reason: Mapped[str] = mapped_column(Text, default="")
    support_count: Mapped[int] = mapped_column(Integer, default=0)
    distinct_paper_count: Mapped[int] = mapped_column(Integer, default=0)
    counter_strength: Mapped[str] = mapped_column(String(16), default="")
    counter_reason: Mapped[str] = mapped_column(Text, default="")
    coverage_status: Mapped[str] = mapped_column(String(16), default="")
    coverage_reason: Mapped[str] = mapped_column(Text, default="")
    coverage_risks: Mapped[list] = mapped_column(JSON, default=list)
    external_search_used: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    human_review_reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")

    project: Mapped[Project] = relationship(back_populates="gaps")


class Task(Base):
    """Workflow task record."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    current_step: Mapped[str] = mapped_column(String(128), default="created")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    logs: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped[Project] = relationship(back_populates="tasks")
