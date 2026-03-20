from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analysis import router as analysis_router
from app.api.export import router as export_router
from app.api.gaps import router as gaps_router
from app.api.papers import router as papers_router
from app.api.projects import router as projects_router
from app.db.models import Base
from app.db.session import engine
from app.utils.file_utils import ensure_app_directories

app = FastAPI(title="Paper Survey Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """Initialize directories and database tables."""

    ensure_app_directories()
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check() -> dict:
    """Simple health endpoint."""

    return {"status": "ok"}


app.include_router(projects_router)
app.include_router(papers_router)
app.include_router(analysis_router)
app.include_router(gaps_router)
app.include_router(export_router)
