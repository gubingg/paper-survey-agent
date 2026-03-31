from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from fastapi import UploadFile


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RAW_PAPERS_DIR = DATA_DIR / "raw_papers"
PAPER_LIBRARY_DIR = RAW_PAPERS_DIR / "library"
PARSED_DIR = DATA_DIR / "parsed"
EXPORTS_DIR = DATA_DIR / "exports"
CHROMA_DIR = DATA_DIR / "chroma"


def ensure_app_directories() -> None:
    """Create application data directories when the app starts."""

    for path in [DATA_DIR, RAW_PAPERS_DIR, PAPER_LIBRARY_DIR, PARSED_DIR, EXPORTS_DIR, CHROMA_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def compute_file_hash(data: bytes) -> str:
    """Return a stable sha256 for uploaded file bytes."""

    return hashlib.sha256(data).hexdigest()


def compute_file_hash_from_path(path: Path) -> str:
    """Return a stable sha256 for an existing file path."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_upload_bytes(upload: UploadFile) -> bytes:
    """Read all bytes from an uploaded file and reset the stream when possible."""

    upload.file.seek(0)
    data = upload.file.read()
    upload.file.seek(0)
    return data


def save_upload_file(project_id: str, upload: UploadFile) -> str:
    """Backward-compatible project-local upload helper."""

    ensure_app_directories()
    project_dir = RAW_PAPERS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    file_path = project_dir / upload.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)
    return str(file_path)


def save_pdf_library_file(file_hash: str, file_name: str, data: bytes) -> str:
    """Persist one canonical PDF copy in the shared paper library."""

    ensure_app_directories()
    suffix = Path(file_name).suffix.lower() or ".pdf"
    file_path = PAPER_LIBRARY_DIR / f"{file_hash}{suffix}"
    if not file_path.exists():
        file_path.write_bytes(data)
    return str(file_path)


def delete_file_if_exists(file_path: str | Path | None) -> None:
    """Delete one file if it exists."""

    if not file_path:
        return
    path = Path(file_path)
    if path.exists() and path.is_file():
        path.unlink(missing_ok=True)


def delete_project_artifacts(project_id: str) -> None:
    """Delete parsed/exported artifacts for one project."""

    for directory in [RAW_PAPERS_DIR / project_id, PARSED_DIR / project_id, EXPORTS_DIR / project_id]:
        if directory.exists():
            shutil.rmtree(directory, ignore_errors=True)


def save_json_artifact(project_id: str, file_name: str, payload: dict) -> str:
    """Persist parsed or exported JSON content for debugging and reuse."""

    ensure_app_directories()
    project_dir = PARSED_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    file_path = project_dir / file_name
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(file_path)


def export_text_file(project_id: str, export_type: str, content: str, suffix: str = ".md") -> str:
    """Write export content to the exports directory."""

    ensure_app_directories()
    project_dir = EXPORTS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    file_path = project_dir / f"{export_type}{suffix}"
    file_path.write_text(content, encoding="utf-8")
    return str(file_path)
