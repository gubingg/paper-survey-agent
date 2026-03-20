from __future__ import annotations

from app.schemas.paper_schema import PaperChunk, ParsedPaper, ParsedPage
from app.services.extraction_service import ExtractionService


def test_heuristic_extraction_returns_schema():
    parsed_paper = ParsedPaper(
        paper_id="paper_001",
        title_guess="Awesome Research Paper",
        pages=[ParsedPage(page=1, text="Abstract\nWe study a recommendation task using MovieLens dataset.")],
        full_text=(
            "Abstract We study a recommendation task using MovieLens dataset. "
            "Method Our transformer model improves NDCG and Recall. "
            "Future work includes robustness evaluation."
        ),
        chunks=[
            PaperChunk(
                chunk_id="chunk_1",
                paper_id="paper_001",
                section="method",
                page_start=1,
                page_end=1,
                content="Method Our transformer model improves NDCG and Recall.",
            )
        ],
    )

    service = ExtractionService()
    schema = service._heuristic_extract(parsed_paper)

    assert schema.paper_id == "paper_001"
    assert schema.title == "Awesome Research Paper"
    assert schema.method_category == "transformer_or_llm"
