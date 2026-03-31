from __future__ import annotations

import re
from collections import Counter

from app.schemas.gap_schema import GapCandidate
from app.schemas.paper_schema import CompareResult, PaperSchema


FOCUS_DIMENSION_LABELS = {
    "methods": "methods",
    "datasets": "datasets",
    "metrics": "metrics",
    "limitations": "limitations",
    "future_work": "future work",
    "research_gap": "research gap",
    "efficiency": "efficiency",
}


class GapService:
    """Service for shared raw gap candidate generation."""

    def generate_gap_candidates(
        self,
        project_id: str,
        paper_schemas: list[PaperSchema],
        compare_result: CompareResult | None,
        focus_dimensions: list[str] | None = None,
        user_requirements: str = "",
    ) -> list[GapCandidate]:
        """Generate preliminary gap candidates for every target type."""

        if not paper_schemas:
            return []

        candidates: list[GapCandidate] = []
        preference_note = self._preference_note(focus_dimensions, user_requirements)
        limitation_counter = Counter(
            limitation.strip()
            for schema in paper_schemas
            for limitation in schema.limitations
            if limitation.strip()
        )
        future_counter = Counter(
            item.strip()
            for schema in paper_schemas
            for item in schema.future_work
            if item.strip()
        )
        dataset_counter = Counter(dataset.strip() for schema in paper_schemas for dataset in schema.datasets if dataset.strip())
        metric_counter = Counter(metric.strip() for schema in paper_schemas for metric in schema.metrics if metric.strip())

        if limitation_counter:
            top_limitation, frequency = limitation_counter.most_common(1)[0]
            evidence = [f"Recurring limitation observed in {frequency} paper(s): {top_limitation}"]
            if preference_note:
                evidence.append(preference_note)
            candidates.append(
                GapCandidate(
                    gap_id=f"gap_{project_id[-4:]}_limitation",
                    project_id=project_id,
                    original_statement=f"Current papers still leave the following issue insufficiently addressed: {top_limitation}",
                    statement=f"Current papers still leave the following issue insufficiently addressed: {top_limitation}",
                    source_context=(compare_result.limitations_summary if compare_result else top_limitation),
                    supporting_papers=[schema.paper_id for schema in paper_schemas if top_limitation in schema.limitations],
                    evidence_summary=evidence,
                    suggested_direction="Turn the shared limitation into a concrete next-step study with clearer scope, datasets, and validation criteria.",
                    status="pending",
                )
            )

        if future_counter:
            top_future, frequency = future_counter.most_common(1)[0]
            evidence = [f"Future-work signal appears in {frequency} paper(s): {top_future}"]
            if preference_note:
                evidence.append(preference_note)
            candidates.append(
                GapCandidate(
                    gap_id=f"gap_{project_id[-4:]}_future",
                    project_id=project_id,
                    original_statement=f"A promising follow-up direction is repeatedly suggested but not yet systematically covered: {top_future}",
                    statement=f"A promising follow-up direction is repeatedly suggested but not yet systematically covered: {top_future}",
                    source_context=top_future,
                    supporting_papers=[schema.paper_id for schema in paper_schemas if top_future in schema.future_work],
                    evidence_summary=evidence,
                    suggested_direction="Translate the repeated future-work suggestion into a scoped experiment plan or method improvement agenda.",
                    status="pending",
                )
            )

        if len(dataset_counter) <= 2 and dataset_counter:
            dataset_names = ", ".join(name for name, _ in dataset_counter.most_common(3))
            evidence = [f"Dataset coverage is concentrated in: {dataset_names}"]
            if preference_note:
                evidence.append(preference_note)
            candidates.append(
                GapCandidate(
                    gap_id=f"gap_{project_id[-4:]}_dataset",
                    project_id=project_id,
                    original_statement="Current evidence appears concentrated on a narrow dataset set, leaving cross-dataset generalization underexplored.",
                    statement="Current evidence appears concentrated on a narrow dataset set, leaving cross-dataset generalization underexplored.",
                    source_context=dataset_names,
                    supporting_papers=[schema.paper_id for schema in paper_schemas if schema.datasets],
                    evidence_summary=evidence,
                    suggested_direction="Extend comparison onto broader datasets, domain shifts, or harder transfer settings.",
                    status="pending",
                )
            )

        if len(metric_counter) <= 2 and metric_counter:
            metric_names = ", ".join(name for name, _ in metric_counter.most_common(3))
            evidence = [f"Evaluation is dominated by: {metric_names}"]
            if preference_note:
                evidence.append(preference_note)
            candidates.append(
                GapCandidate(
                    gap_id=f"gap_{project_id[-4:]}_metric",
                    project_id=project_id,
                    original_statement="Current evaluation focuses on a narrow metric view, leaving broader performance trade-offs insufficiently assessed.",
                    statement="Current evaluation focuses on a narrow metric view, leaving broader performance trade-offs insufficiently assessed.",
                    source_context=metric_names,
                    supporting_papers=[schema.paper_id for schema in paper_schemas if schema.metrics],
                    evidence_summary=evidence,
                    suggested_direction="Add robustness, efficiency, calibration, or user-facing utility metrics to strengthen evaluation coverage.",
                    status="pending",
                )
            )

        if not candidates and compare_result is not None:
            evidence = [compare_result.cross_paper_summary or compare_result.trend_summary]
            if preference_note:
                evidence.append(preference_note)
            candidates.append(
                GapCandidate(
                    gap_id=f"gap_{project_id[-4:]}_general",
                    project_id=project_id,
                    original_statement="The current paper set reveals partially aligned directions, but several open questions still need clearer validation and broader coverage.",
                    statement="The current paper set reveals partially aligned directions, but several open questions still need clearer validation and broader coverage.",
                    source_context=compare_result.cross_paper_summary or compare_result.trend_summary,
                    supporting_papers=[row.paper_id for row in compare_result.rows],
                    evidence_summary=evidence,
                    suggested_direction="Use the cross-paper comparison to isolate one high-value unanswered question and define a measurable validation path.",
                    status="pending",
                )
            )

        return candidates[:4]

    @staticmethod
    def _preference_note(focus_dimensions: list[str] | None, user_requirements: str) -> str:
        notes: list[str] = []
        if focus_dimensions:
            labels = [FOCUS_DIMENSION_LABELS.get(item, item) for item in focus_dimensions]
            notes.append(f"Priority focus: {', '.join(labels)}")
        if user_requirements.strip():
            notes.append(f"User requirement: {user_requirements.strip()}")
        return " | ".join(notes)

    @staticmethod
    def extract_gap_keywords(statement: str) -> list[str]:
        """Extract keywords from a gap statement for retrieval use."""

        return [token for token in re.findall(r"[A-Za-z\u4e00-\u9fff0-9\-]+", statement.lower()) if len(token) > 1][:10]
