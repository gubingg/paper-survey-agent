from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Paper, ProjectPaper
from app.utils.file_utils import compute_file_hash_from_path


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./paper_survey_agent.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _column_names(table_name: str) -> set[str]:
    inspector = inspect(engine)
    try:
        return {column["name"] for column in inspector.get_columns(table_name)}
    except Exception:
        return set()


def _ensure_papers_columns() -> None:
    columns = _column_names("papers")
    with engine.begin() as connection:
        if "file_hash" not in columns:
            connection.execute(text("ALTER TABLE papers ADD COLUMN file_hash TEXT DEFAULT ''"))
        if "original_filename" not in columns:
            connection.execute(text("ALTER TABLE papers ADD COLUMN original_filename TEXT DEFAULT ''"))


def _ensure_projects_columns() -> None:
    columns = _column_names("projects")
    with engine.begin() as connection:
        if "focus_dimensions" not in columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN focus_dimensions JSON DEFAULT '[]'"))
        if "domain_hint" not in columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN domain_hint TEXT DEFAULT ''"))
        if "user_requirements" not in columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN user_requirements TEXT DEFAULT ''"))
        if "gap_validation_level" not in columns:
            connection.execute(text("ALTER TABLE projects ADD COLUMN gap_validation_level TEXT DEFAULT ''"))


def _backfill_project_paper_links() -> None:
    with SessionLocal() as db:
        papers = list(db.scalars(select(Paper)))
        changed = False
        for paper in papers:
            if not paper.project_id:
                continue
            link = db.get(ProjectPaper, {"project_id": paper.project_id, "paper_id": paper.id})
            if link is None:
                db.add(ProjectPaper(project_id=paper.project_id, paper_id=paper.id))
                changed = True
        if changed:
            db.commit()


def _backfill_paper_metadata() -> None:
    with SessionLocal() as db:
        papers = list(db.scalars(select(Paper)))
        changed = False
        for paper in papers:
            if not paper.original_filename and paper.file_path:
                paper.original_filename = Path(paper.file_path).name
                changed = True
            if not paper.file_hash and paper.file_path:
                path = Path(paper.file_path)
                if path.exists():
                    paper.file_hash = compute_file_hash_from_path(path)
                    changed = True
        if changed:
            db.commit()


def _ensure_gap_candidate_columns() -> None:
    columns = _column_names("gap_candidates")
    with engine.begin() as connection:
        additions = {
            "validation_level": "ALTER TABLE gap_candidates ADD COLUMN validation_level TEXT DEFAULT 'raw'",
            "original_statement": "ALTER TABLE gap_candidates ADD COLUMN original_statement TEXT DEFAULT ''",
            "source_context": "ALTER TABLE gap_candidates ADD COLUMN source_context TEXT DEFAULT ''",
            "validation_reason": "ALTER TABLE gap_candidates ADD COLUMN validation_reason TEXT DEFAULT ''",
            "normalized_gap": "ALTER TABLE gap_candidates ADD COLUMN normalized_gap JSON DEFAULT '{}'",
            "support_strength": "ALTER TABLE gap_candidates ADD COLUMN support_strength TEXT DEFAULT ''",
            "support_reason": "ALTER TABLE gap_candidates ADD COLUMN support_reason TEXT DEFAULT ''",
            "support_count": "ALTER TABLE gap_candidates ADD COLUMN support_count INTEGER DEFAULT 0",
            "distinct_paper_count": "ALTER TABLE gap_candidates ADD COLUMN distinct_paper_count INTEGER DEFAULT 0",
            "counter_strength": "ALTER TABLE gap_candidates ADD COLUMN counter_strength TEXT DEFAULT ''",
            "counter_reason": "ALTER TABLE gap_candidates ADD COLUMN counter_reason TEXT DEFAULT ''",
            "coverage_status": "ALTER TABLE gap_candidates ADD COLUMN coverage_status TEXT DEFAULT ''",
            "coverage_reason": "ALTER TABLE gap_candidates ADD COLUMN coverage_reason TEXT DEFAULT ''",
            "coverage_risks": "ALTER TABLE gap_candidates ADD COLUMN coverage_risks JSON DEFAULT '[]'",
            "external_search_used": "ALTER TABLE gap_candidates ADD COLUMN external_search_used BOOLEAN DEFAULT 0",
            "human_review_reason": "ALTER TABLE gap_candidates ADD COLUMN human_review_reason TEXT DEFAULT ''",
        }
        for column_name, ddl in additions.items():
            if column_name not in columns:
                connection.execute(text(ddl))


def initialize_database() -> None:
    """Create tables and apply lightweight compatibility migrations."""

    Base.metadata.create_all(bind=engine)
    _ensure_papers_columns()
    _ensure_projects_columns()
    _ensure_gap_candidate_columns()
    Base.metadata.create_all(bind=engine)
    _backfill_project_paper_links()
    _backfill_paper_metadata()


def get_db():
    """Yield a database session for FastAPI dependencies."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
