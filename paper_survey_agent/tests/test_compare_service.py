from __future__ import annotations

import json

from app.schemas.paper_schema import PaperSchema
from app.services.compare_service import CompareService


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self._content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self._content}}]}


def test_compare_service_builds_summary():
    service = CompareService()
    service.api_key = ""
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


def test_compare_service_uses_llm_to_interpret_user_requirements(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["prompt"] = json["messages"][1]["content"]
        return _FakeResponse(
            json_module.dumps(
                {
                    "cross_paper_summary": "LLM summary focused on generalization.",
                    "method_comparison": ["LLM says compare generalization first"],
                    "limitations_summary": "LLM limitations summary.",
                },
                ensure_ascii=False,
            )
        )

    json_module = json
    monkeypatch.setattr("app.services.compare_service.requests.post", fake_post)
    service = CompareService()
    service.api_key = "test-key"

    result = service.build_compare_result(
        [
            PaperSchema(
                paper_id="paper_1",
                title="Paper One",
                research_problem="Problem A",
                method="Method A",
                method_category="transformer_or_llm",
                datasets=["MovieLens"],
                metrics=["NDCG"],
                limitations=["Lack of cross-domain validation."],
            )
        ],
        topic="Recommendation",
        user_requirements="Focus on generalization and cross-dataset evidence.",
    )

    assert "Focus on generalization and cross-dataset evidence." in captured["prompt"]
    assert result.cross_paper_summary == "LLM summary focused on generalization."
    assert result.method_comparison == ["LLM says compare generalization first"]
    assert result.limitations_summary == "LLM limitations summary."


def test_compare_service_generates_raw_gap_candidates_from_comparison():
    service = CompareService()
    service.api_key = ""
    schemas = [
        PaperSchema(
            paper_id="paper_1",
            title="Paper One",
            research_problem="Problem A",
            method="Method A",
            datasets=["MovieLens"],
            metrics=["NDCG"],
            limitations=["Only evaluated on one dataset."],
            future_work=["Evaluate on more datasets."],
        ),
        PaperSchema(
            paper_id="paper_2",
            title="Paper Two",
            research_problem="Problem B",
            method="Method B",
            datasets=["MovieLens"],
            metrics=["NDCG"],
            limitations=["Only evaluated on one dataset."],
            future_work=["Evaluate on more datasets."],
        ),
    ]
    compare_result = service.build_compare_result(schemas, topic="Recommendation")

    candidates = service.generate_gap_candidates_raw(
        project_id="proj_1",
        paper_schemas=schemas,
        compare_result=compare_result,
        focus_dimensions=["research_gap"],
        user_requirements="Focus on future work.",
    )

    assert candidates
    assert candidates[0].project_id == "proj_1"
