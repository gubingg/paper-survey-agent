from __future__ import annotations

from app.graph.edges import STRICT_GAP_VALIDATION_NODE, route_after_gap_generation
from app.schemas.agent_schema import EvidenceSnippet
from app.schemas.gap_schema import GapCandidate
from app.schemas.graph_state import MainWorkflowState
from app.schemas.paper_schema import CompareMatrixRow, CompareResult, PaperSchema
from app.services.gap_service import GapService
from app.services.gap_validation_service import GapValidationService
from app.utils.gap_validation_utils import resolve_gap_validation_level


def test_gap_service_generates_raw_candidates_for_all_targets():
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
    compare_result = CompareResult(
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
        limitations_summary="Shared limitations summary.",
    )

    candidates = service.generate_gap_candidates("proj_1", schemas, compare_result)

    assert candidates
    assert candidates[0].project_id == "proj_1"
    assert candidates[0].original_statement
    assert candidates[0].source_context


def test_light_gap_validation_softens_when_support_is_weak():
    service = GapValidationService()
    candidate = GapCandidate(
        gap_id="gap_1",
        project_id="proj_1",
        original_statement="Current papers still leave multimodal fusion underexplored.",
        statement="Current papers still leave multimodal fusion underexplored.",
    )
    evidence = [
        EvidenceSnippet(paper_id="paper_1", content="The paper notes multimodal fusion remains challenging.", score=0.015),
    ]

    status, revised_text, reason, confidence = service.judge_light_gap_candidate(candidate, evidence)

    assert status == "weakened"
    assert revised_text != candidate.original_statement
    assert "wording" in reason.lower()
    assert 0 < confidence < 1


def test_strict_gap_decision_distinguishes_confirmed_and_rejected():
    service = GapValidationService()

    confirmed = service.final_gap_decision("high", "low", "sufficient")
    rejected = service.final_gap_decision("low", "high", "limited")

    assert confirmed[0] == "confirmed_gap"
    assert rejected[0] == "rejected"


def test_resolve_gap_validation_level_defaults_by_target_type():
    assert resolve_gap_validation_level("survey") == "light"
    assert resolve_gap_validation_level("meeting_outline") == "light"
    assert resolve_gap_validation_level("gap_analysis") == "strict"
    assert resolve_gap_validation_level("survey", user_override="off") == "off"


def test_resolve_gap_validation_level_honors_explicit_override():
    assert resolve_gap_validation_level("gap_analysis", user_override="light") == "light"
    assert resolve_gap_validation_level("survey", user_override="strict") == "strict"


def test_gap_generation_route_uses_effective_validation_level():
    state = MainWorkflowState(
        project_id="proj_1",
        target_type="survey",
        gap_validation_level="light",
        effective_validation_level="strict",
        gap_candidates_raw=[
            GapCandidate(
                gap_id="gap_1",
                project_id="proj_1",
                original_statement="Current papers still leave multimodal fusion underexplored.",
                statement="Current papers still leave multimodal fusion underexplored.",
            )
        ],
    )

    assert route_after_gap_generation(state) == STRICT_GAP_VALIDATION_NODE
