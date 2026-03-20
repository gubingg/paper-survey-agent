from __future__ import annotations

from app.schemas.paper_schema import PaperSchema
from app.services.compare_service import CompareService


def test_compare_service_builds_summary():
    service = CompareService()
    result = service.build_compare_result(
        [
            PaperSchema(
                paper_id="paper_1",
                title="Paper One",
                research_problem="Problem A",
                method="Method A",
                method_category="transformer_or_llm",
                datasets=["MovieLens"],
                metrics=["NDCG", "Recall"],
                limitations=["Lack of cross-domain validation."],
            ),
            PaperSchema(
                paper_id="paper_2",
                title="Paper Two",
                research_problem="Problem B",
                method="Method B",
                method_category="graph_based",
                datasets=["Amazon"],
                metrics=["NDCG"],
                limitations=["Lack of cross-domain validation."],
            ),
        ],
        topic="Recommendation",
    )

    assert len(result.rows) == 2
    assert "Recommendation" in result.trend_summary
    assert result.dataset_trends
