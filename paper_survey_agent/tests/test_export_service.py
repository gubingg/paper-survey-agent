from __future__ import annotations

import sys
import types

sys.modules.setdefault("fastapi", types.SimpleNamespace(UploadFile=object))

from app.schemas.agent_schema import EvidenceSnippet
from app.schemas.gap_schema import GapCandidate
from app.schemas.paper_schema import CompareMatrixRow, CompareResult, PaperSchema
from app.services.export_service import ExportService


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self._content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self._content}}]}


def _sample_compare_result() -> CompareResult:
    return CompareResult(
        rows=[
            CompareMatrixRow(
                paper_id="paper_1",
                title="Paper One",
                research_problem="Problem A",
                method="Method A",
                datasets=["MovieLens"],
                metrics=["NDCG"],
                limitations=["Only evaluated on one dataset."],
            )
        ],
        trend_summary="Cross-paper summary.",
        cross_paper_summary="Cross-paper summary.",
        method_comparison=["transformer_or_llm: 1 paper(s)"],
        limitations_summary="Shared limitations summary.",
    )


def _sample_paper_schema() -> PaperSchema:
    return PaperSchema(
        paper_id="paper_1",
        title="Paper One",
        research_problem="Problem A",
        method="Method A",
        datasets=["MovieLens"],
        metrics=["NDCG"],
        main_results="Improves NDCG on MovieLens.",
        limitations=["Only evaluated on one dataset."],
        future_work=["Evaluate on more datasets."],
    )


def _sample_gap_candidate() -> GapCandidate:
    return GapCandidate(
        gap_id="gap_1",
        project_id="proj_1",
        original_statement="Current papers still leave cross-dataset generalization underexplored.",
        statement="Current papers still leave cross-dataset generalization underexplored.",
        validation_result="confirmed_gap",
        validation_level="strict",
        confidence=0.86,
        coverage_count=3,
        coverage_status="sufficient",
        validation_reason="Support is strong, counter-evidence is weak, and coverage is sufficient.",
        suggested_direction="Evaluate on broader datasets and harder transfer settings.",
        supporting_evidence=[
            EvidenceSnippet(
                paper_id="paper_1",
                page_start=3,
                page_end=3,
                content="The paper evaluates on a single benchmark and notes generalization remains open.",
                score=0.8,
            )
        ],
        counter_evidence=[
            EvidenceSnippet(
                paper_id="paper_2",
                page_start=5,
                page_end=5,
                content="A related paper partially addresses transfer robustness, but coverage remains limited.",
                score=0.3,
            )
        ],
        requires_human_review=True,
        human_review_reason="limited coverage",
        support_strength="high",
        counter_strength="low",
    )


def test_generate_output_keeps_survey_focus_even_with_strict_validation(monkeypatch):
    monkeypatch.setattr("app.services.export_service.export_text_file", lambda project_id, export_type, content, suffix=".md": f"{project_id}/{export_type}{suffix}")
    service = ExportService()
    service.api_key = ""

    payload = service.generate_output(
        task_type="survey",
        project_id="proj_1",
        topic="Recommendation",
        paper_schemas=[_sample_paper_schema()],
        compare_result=_sample_compare_result(),
        gap_candidates=[_sample_gap_candidate()],
        effective_validation_level="strict",
    )

    assert payload.export_type == "survey"
    assert "## Research Landscape" in payload.content
    assert "## Limitations and Future Directions" in payload.content
    assert "## Final Gap Candidates" not in payload.content
    assert "Validation result:" not in payload.content


def test_generate_output_uses_llm_to_interpret_user_requirements(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["prompt"] = json["messages"][1]["content"]
        return _FakeResponse("# Meeting Outline\n\nLLM organized output for the requested focus.")

    monkeypatch.setattr("app.services.export_service.requests.post", fake_post)
    monkeypatch.setattr("app.services.export_service.export_text_file", lambda project_id, export_type, content, suffix=".md": f"{project_id}/{export_type}{suffix}")
    service = ExportService()
    service.api_key = "test-key"

    payload = service.generate_output(
        task_type="meeting_outline",
        project_id="proj_1",
        topic="Recommendation",
        paper_schemas=[_sample_paper_schema()],
        compare_result=_sample_compare_result(),
        gap_candidates=[_sample_gap_candidate()],
        user_requirements="Emphasize method differences and discussion questions for a lab meeting.",
        effective_validation_level="strict",
    )

    assert "Emphasize method differences and discussion questions for a lab meeting." in captured["prompt"]
    assert payload.content == "# Meeting Outline\n\nLLM organized output for the requested focus."


def test_generate_output_keeps_meeting_outline_focus_even_with_strict_validation(monkeypatch):
    monkeypatch.setattr("app.services.export_service.export_text_file", lambda project_id, export_type, content, suffix=".md": f"{project_id}/{export_type}{suffix}")
    service = ExportService()
    service.api_key = ""

    payload = service.generate_output(
        task_type="meeting_outline",
        project_id="proj_1",
        topic="Recommendation",
        paper_schemas=[_sample_paper_schema()],
        compare_result=_sample_compare_result(),
        gap_candidates=[_sample_gap_candidate()],
        effective_validation_level="strict",
    )

    assert payload.export_type == "meeting_outline"
    assert "## Representative Papers" in payload.content
    assert "## Discussion Directions" in payload.content
    assert "## Final Gap Candidates" not in payload.content
    assert "Validation result:" not in payload.content


def test_generate_output_uses_gap_analysis_structure_for_gap_task(monkeypatch):
    monkeypatch.setattr("app.services.export_service.export_text_file", lambda project_id, export_type, content, suffix=".md": f"{project_id}/{export_type}{suffix}")
    service = ExportService()
    service.api_key = ""

    payload = service.generate_output(
        task_type="gap_analysis",
        project_id="proj_1",
        topic="Recommendation",
        paper_schemas=[_sample_paper_schema()],
        compare_result=_sample_compare_result(),
        gap_candidates=[_sample_gap_candidate()],
        effective_validation_level="strict",
    )

    assert payload.export_type == "gap_analysis"
    assert "## Final Gap Candidates" in payload.content
    assert "- Validation result: confirmed_gap" in payload.content
    assert "- Confidence: 0.86" in payload.content
    assert "- Coverage: 3 paper(s) / sufficient" in payload.content
    assert "- Supporting evidence:" in payload.content
    assert "- Counter evidence:" in payload.content
    assert "- Human review: yes (limited coverage)" in payload.content


def test_export_wrapper_still_supports_compare_table(monkeypatch):
    monkeypatch.setattr("app.services.export_service.export_text_file", lambda project_id, export_type, content, suffix=".md": f"{project_id}/{export_type}{suffix}")
    service = ExportService()
    service.api_key = ""

    payload = service.export(
        project_id="proj_1",
        export_type="compare_table",
        topic="Recommendation",
        paper_schemas=[_sample_paper_schema()],
        compare_result=_sample_compare_result(),
        gap_candidates=[_sample_gap_candidate()],
    )

    assert payload.export_type == "compare_table"
    assert "| Title | Problem | Method | Datasets | Metrics | Limitations |" in payload.content
