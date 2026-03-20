from __future__ import annotations

from app.schemas.paper_schema import PaperSchema
from app.services.field_completion_service import FieldCompletionService


def test_detect_problem_fields_and_generate_fill_query():
    service = FieldCompletionService()
    schema = PaperSchema(
        paper_id="paper_1",
        title="Paper One",
        research_problem="Problem A",
        method="Method A",
        datasets=[],
        metrics=["NDCG"],
        limitations=["N/A"],
        future_work=[],
    )

    problems = service.detect_problem_fields(schema)

    field_names = {item.field_name for item in problems}
    assert "datasets" in field_names
    assert "limitations" in field_names
    assert "future_work" in field_names
    assert "dataset" in service.build_retrieval_query("datasets", [])
