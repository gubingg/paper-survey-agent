from __future__ import annotations

from app.schemas.gap_schema import EnrichmentEvidence, MissingFieldResult
from app.schemas.paper_schema import PaperSchema


class EnrichmentService:
    """Placeholder service for external evidence retrieval."""

    def enrich_missing_fields(
        self,
        paper_schemas: list[PaperSchema],
        missing_fields: dict[str, MissingFieldResult],
    ) -> list[EnrichmentEvidence]:
        """Return an empty list for the MVP while preserving the service boundary."""

        _ = (paper_schemas, missing_fields)
        return []
