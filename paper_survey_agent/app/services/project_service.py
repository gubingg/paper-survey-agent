from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.db import crud
from app.schemas.api_schema import DeleteProjectResponse, ProjectListResponse, UploadPapersResponse
from app.services.vector_store_service import VectorStoreService
from app.utils.file_utils import (
    compute_file_hash,
    delete_file_if_exists,
    delete_project_artifacts,
    read_upload_bytes,
    save_pdf_library_file,
)


class ProjectService:
    """Service for project management, shared-paper uploads, and cleanup."""

    def __init__(self) -> None:
        self.vector_store_service = VectorStoreService()

    def list_projects(self, db: Session) -> ProjectListResponse:
        return ProjectListResponse(projects=crud.list_projects(db))

    def upload_papers(self, db: Session, project_id: str, files: list[UploadFile]) -> UploadPapersResponse:
        paper_ids: list[str] = []
        file_paths: list[str] = []
        reused_paper_ids: list[str] = []
        newly_stored_paper_ids: list[str] = []
        processed_hashes: set[str] = set()

        for upload in files:
            suffix = Path(upload.filename or "").suffix.lower()
            if suffix != ".pdf":
                raise ValueError(f"Only PDF files are allowed: {upload.filename}")

            file_bytes = read_upload_bytes(upload)
            file_hash = compute_file_hash(file_bytes)
            if file_hash in processed_hashes:
                continue
            processed_hashes.add(file_hash)

            existing = crud.get_paper_by_hash(db, file_hash)
            if existing is None or not Path(existing.file_path).exists():
                file_path = save_pdf_library_file(file_hash, upload.filename or "paper.pdf", file_bytes)
            else:
                file_path = existing.file_path

            paper, created_new, linked_new = crud.create_or_link_paper(
                db,
                project_id,
                file_path=file_path,
                file_hash=file_hash,
                title=Path(upload.filename or "").stem,
                original_filename=upload.filename or "",
            )
            if linked_new:
                paper_ids.append(paper.id)
                file_paths.append(file_path)
            if created_new:
                newly_stored_paper_ids.append(paper.id)
            else:
                reused_paper_ids.append(paper.id)

        return UploadPapersResponse(
            paper_ids=paper_ids,
            file_paths=file_paths,
            reused_paper_ids=sorted(set(reused_paper_ids)),
            newly_stored_paper_ids=sorted(set(newly_stored_paper_ids)),
        )

    def delete_project(self, db: Session, project_id: str) -> DeleteProjectResponse:
        project = crud.get_project(db, project_id)
        if project is None:
            raise ValueError("Project not found.")

        linked_papers = crud.list_project_papers(db, project_id)
        deleted_paper_ids: list[str] = []
        retained_shared_paper_ids: list[str] = []
        orphan_file_paths: dict[str, str] = {}

        for paper in linked_papers:
            other_projects = crud.list_other_project_ids_for_paper(db, paper.id, excluding_project_id=project_id)
            if other_projects:
                retained_shared_paper_ids.append(paper.id)
                if paper.project_id == project_id:
                    crud.update_paper_owner_project(db, paper.id, other_projects[0])
            else:
                deleted_paper_ids.append(paper.id)
                orphan_file_paths[paper.id] = paper.file_path

        for paper_id in deleted_paper_ids:
            self.vector_store_service.delete_paper_chunks(paper_id)
            crud.delete_paper_asset(db, paper_id)
            delete_file_if_exists(orphan_file_paths.get(paper_id))

        crud.delete_project_records(db, project_id)
        delete_project_artifacts(project_id)

        return DeleteProjectResponse(
            project_id=project_id,
            deleted=True,
            deleted_paper_ids=deleted_paper_ids,
            retained_shared_paper_ids=retained_shared_paper_ids,
        )
