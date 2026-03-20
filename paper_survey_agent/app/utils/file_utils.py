from __future__ import annotations

import json
import shutil
from pathlib import Path

from fastapi import UploadFile


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RAW_PAPERS_DIR = DATA_DIR / "raw_papers"
PARSED_DIR = DATA_DIR / "parsed"
EXPORTS_DIR = DATA_DIR / "exports"
CHROMA_DIR = DATA_DIR / "chroma"


def ensure_app_directories() -> None:
    """Create application data directories when the app starts."""

    for path in [DATA_DIR, RAW_PAPERS_DIR, PARSED_DIR, EXPORTS_DIR, CHROMA_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def save_upload_file(project_id: str, upload: UploadFile) -> str:
    """Persist an uploaded PDF to the raw paper directory."""

    ensure_app_directories()
    project_dir = RAW_PAPERS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    file_path = project_dir / upload.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)
    return str(file_path)


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
