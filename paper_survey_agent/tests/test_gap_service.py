from __future__ import annotations

from app.schemas.gap_schema import GapCandidate
from app.schemas.paper_schema import CompareMatrixRow, CompareResult, PaperSchema
from app.services.gap_service import GapService
from app.services.gap_validation_service import GapValidationService
from app.schemas.agent_schema import EvidenceSnippet


def test_gap_service_generates_candidates():
    service = GapService()
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
    compare_result = CompareResult(rows=[CompareMatrixRow(
        paper_id="paper_1",
        title="Paper One",
        research_problem="Problem A",
        method="Method A",
        datasets=["MovieLens"],
        metrics=["NDCG"],
        limitations=["Only evaluated on one dataset."],
    )])

    candidates = service.generate_gap_candidates("proj_1", schemas, compare_result)

    assert candidates
    assert candidates[0].project_id == "proj_1"


def test_gap_validation_service_judges_support_and_conflict():
    service = GapValidationService()
    candidate = GapCandidate(
        gap_id="gap_1",
        project_id="proj_1",
        statement="Current datasets are too narrow.",
        supporting_papers=["paper_1", "paper_2"],
    )
    supporting = [
        EvidenceSnippet(paper_id="paper_1", content="Only one dataset is used.", score=0.03),
        EvidenceSnippet(paper_id="paper_2", content="Experiments focus on a single benchmark.", score=0.03),
    ]
    counter = [EvidenceSnippet(paper_id="paper_3", content="This work uses many datasets.", score=0.01)]

    result, confidence, requires_review = service.judge_gap_evidence(supporting, counter, coverage_count=2)

    assert result in {"成立", "有冲突"}
    assert confidence > 0
    assert isinstance(requires_review, bool)
