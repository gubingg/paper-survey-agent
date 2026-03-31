from __future__ import annotations

import json
import os
from pathlib import Path

import requests

from app.schemas.gap_schema import GapCandidate
from app.schemas.paper_schema import CompareResult, ExportPayload, PaperSchema
from app.utils.file_utils import export_text_file
from app.utils.logger import get_logger


FOCUS_DIMENSION_LABELS = {
    "methods": "methods",
    "datasets": "datasets",
    "metrics": "metrics",
    "limitations": "limitations",
    "future_work": "future work",
    "research_gap": "research gap",
    "efficiency": "efficiency",
}

DEFAULT_UNSPECIFIED_TEXT = "Not specified"
DEFAULT_PENDING_TEXT = "Pending extraction"
CORE_TASK_TYPES = {"survey", "meeting_outline", "gap_analysis"}
EXPORT_TYPES = CORE_TASK_TYPES | {"compare_table", "related_work_markdown"}
logger = get_logger(__name__)
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


class ExportService:
    """generate-output skill: organize final user-facing artifacts by task type."""

    def __init__(self) -> None:
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.model_name = os.getenv("QWEN_MODEL_NAME", "qwen3-max")
        self.base_url = os.getenv(
            "QWEN_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        )
        self.timeout = int(os.getenv("QWEN_TIMEOUT", "180"))
        self.prompt_template = self._load_prompt_template()

    @staticmethod
    def normalize_task_type(task_type: str) -> str:
        return task_type if task_type in CORE_TASK_TYPES else "meeting_outline"

    def generate_output(
        self,
        *,
        task_type: str,
        project_id: str,
        topic: str,
        paper_schemas: list[PaperSchema],
        compare_result: CompareResult | None,
        gap_candidates: list[GapCandidate],
        focus_dimensions: list[str] | None = None,
        user_requirements: str = "",
        effective_validation_level: str | None = None,
        validation_details: list[GapCandidate] | None = None,
    ) -> ExportPayload:
        """Generate the final output for survey, meeting_outline, or gap_analysis."""

        normalized_task_type = self.normalize_task_type(task_type)
        selected_gaps = self.select_export_gap_candidates(normalized_task_type, gap_candidates)
        content = self._build_output_content(
            task_type=normalized_task_type,
            topic=topic,
            paper_schemas=paper_schemas,
            compare_result=compare_result,
            gap_candidates=selected_gaps,
            focus_dimensions=focus_dimensions,
            user_requirements=user_requirements,
            effective_validation_level=effective_validation_level,
            validation_details=validation_details,
        )

        file_path = export_text_file(project_id, normalized_task_type, content)
        return ExportPayload(export_type=normalized_task_type, content=content, file_path=file_path)

    def _build_output_content(
        self,
        *,
        task_type: str,
        topic: str,
        paper_schemas: list[PaperSchema],
        compare_result: CompareResult | None,
        gap_candidates: list[GapCandidate],
        focus_dimensions: list[str] | None,
        user_requirements: str,
        effective_validation_level: str | None,
        validation_details: list[GapCandidate] | None,
    ) -> str:
        if self.api_key:
            try:
                return self._generate_output_with_llm(
                    task_type=task_type,
                    topic=topic,
                    paper_schemas=paper_schemas,
                    compare_result=compare_result,
                    gap_candidates=gap_candidates,
                    focus_dimensions=focus_dimensions,
                    user_requirements=user_requirements,
                    effective_validation_level=effective_validation_level,
                    validation_details=validation_details,
                )
            except Exception as exc:
                logger.warning("Export LLM generation failed, falling back to deterministic builder: %s", exc)

        if task_type == "survey":
            return self._build_survey_export(topic, paper_schemas, compare_result, gap_candidates, focus_dimensions, user_requirements)
        if task_type == "gap_analysis":
            return self._build_gap_analysis_export(topic, compare_result, gap_candidates, focus_dimensions, user_requirements)
        return self._build_meeting_outline(topic, paper_schemas, compare_result, gap_candidates, focus_dimensions, user_requirements)

    def _generate_output_with_llm(
        self,
        *,
        task_type: str,
        topic: str,
        paper_schemas: list[PaperSchema],
        compare_result: CompareResult | None,
        gap_candidates: list[GapCandidate],
        focus_dimensions: list[str] | None,
        user_requirements: str,
        effective_validation_level: str | None,
        validation_details: list[GapCandidate] | None,
    ) -> str:
        focus_labels = [FOCUS_DIMENSION_LABELS.get(item, item) for item in (focus_dimensions or [])]
        schema_briefs = [
            {
                "title": schema.title,
                "research_problem": schema.research_problem,
                "method": schema.method,
                "datasets": schema.datasets,
                "metrics": schema.metrics,
                "main_results": schema.main_results,
                "limitations": schema.limitations[:3],
                "future_work": schema.future_work[:3],
            }
            for schema in paper_schemas
        ]
        gap_briefs = [
            {
                "statement": gap.statement,
                "validation_result": gap.validation_result,
                "validation_level": gap.validation_level,
                "confidence": gap.confidence,
                "coverage": gap.coverage_status or gap.coverage_count,
                "suggested_direction": gap.suggested_direction,
                "requires_human_review": gap.requires_human_review,
            }
            for gap in (validation_details or gap_candidates)
        ]
        prompt = (
            f"{self.prompt_template}\n\n"
            "Understand the user requirements before deciding emphasis and ordering. "
            "You must obey task_type boundaries: survey must stay survey-focused, meeting_outline must stay outline-focused, and gap_analysis must foreground validation details. "
            "Return final Markdown only.\n\n"
            f"Task type: {task_type}\n"
            f"Effective validation level: {effective_validation_level or 'not specified'}\n"
            f"Topic: {topic or 'Not specified'}\n"
            f"Focus dimensions: {', '.join(focus_labels) if focus_labels else 'Not specified'}\n"
            f"User requirements: {user_requirements.strip() or 'None'}\n\n"
            f"Compare summary JSON:\n{json.dumps(compare_result.model_dump() if compare_result else {}, ensure_ascii=False)}\n\n"
            f"Paper summaries JSON:\n{json.dumps(schema_briefs, ensure_ascii=False)}\n\n"
            f"Validated gap summaries JSON:\n{json.dumps(gap_briefs, ensure_ascii=False)}"
        )
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You generate final markdown outputs for research analysis tasks."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(self.base_url, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return str(content).strip()

    def export(
        self,
        project_id: str,
        export_type: str,
        topic: str,
        paper_schemas: list[PaperSchema],
        compare_result: CompareResult | None,
        gap_candidates: list[GapCandidate],
        focus_dimensions: list[str] | None = None,
        user_requirements: str = "",
    ) -> ExportPayload:
        """Backward-compatible wrapper for existing callers."""

        normalized_type = export_type if export_type in EXPORT_TYPES else "meeting_outline"
        if normalized_type == "compare_table":
            content = self._build_compare_table(compare_result)
            file_path = export_text_file(project_id, normalized_type, content)
            return ExportPayload(export_type=normalized_type, content=content, file_path=file_path)

        return self.generate_output(
            task_type=self.normalize_task_type(normalized_type),
            project_id=project_id,
            topic=topic,
            paper_schemas=paper_schemas,
            compare_result=compare_result,
            gap_candidates=gap_candidates,
            focus_dimensions=focus_dimensions,
            user_requirements=user_requirements,
        )

    @staticmethod
    def select_export_gap_candidates(task_type: str, gap_candidates: list[GapCandidate]) -> list[GapCandidate]:
        if task_type in {"survey", "meeting_outline"}:
            return [gap for gap in gap_candidates if gap.validation_result in {"supported", "weakened", "raw_candidate", "confirmed_gap", "likely_gap"}]
        if task_type == "gap_analysis":
            return [gap for gap in gap_candidates if gap.validation_result in {"confirmed_gap", "likely_gap"}]
        return gap_candidates

    @staticmethod
    def _preference_block(focus_dimensions: list[str] | None, user_requirements: str) -> list[str]:
        lines = ["## Preferences"]
        if focus_dimensions:
            focus_labels = [FOCUS_DIMENSION_LABELS.get(item, item) for item in focus_dimensions]
            lines.append(f"- Focus dimensions: {', '.join(focus_labels)}")
        else:
            lines.append(f"- Focus dimensions: {DEFAULT_UNSPECIFIED_TEXT}")
        lines.append(f"- User requirements: {user_requirements.strip() or DEFAULT_UNSPECIFIED_TEXT}")
        lines.append("")
        return lines

    @staticmethod
    def _build_compare_table(compare_result: CompareResult | None) -> str:
        if compare_result is None or not compare_result.rows:
            return "# Compare Table\n\nNo comparison data is available yet."

        lines = [
            "# Compare Table",
            "",
            "| Title | Problem | Method | Datasets | Metrics | Limitations |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for row in compare_result.rows:
            lines.append(
                "| {title} | {problem} | {method} | {datasets} | {metrics} | {limitations} |".format(
                    title=row.title.replace("|", "/"),
                    problem=row.research_problem.replace("|", "/")[:120],
                    method=row.method.replace("|", "/")[:120],
                    datasets=", ".join(row.datasets) or "-",
                    metrics=", ".join(row.metrics) or "-",
                    limitations="; ".join(row.limitations[:2]).replace("|", "/") or "-",
                )
            )
        return "\n".join(lines)

    def _build_meeting_outline(self, topic: str, paper_schemas: list[PaperSchema], compare_result: CompareResult | None, gap_candidates: list[GapCandidate], focus_dimensions: list[str] | None, user_requirements: str) -> str:
        lines = ["# Meeting Outline", "", "## Topic", topic or "Topic not provided", ""]
        lines.extend(self._preference_block(focus_dimensions, user_requirements))
        lines.append("## Representative Papers")
        for index, schema in enumerate(paper_schemas, start=1):
            lines.extend([
                f"### {index}. {schema.title}",
                f"- Problem: {schema.research_problem or DEFAULT_PENDING_TEXT}",
                f"- Method: {schema.method or DEFAULT_PENDING_TEXT}",
                f"- Datasets: {', '.join(schema.datasets) if schema.datasets else DEFAULT_PENDING_TEXT}",
                f"- Metrics: {', '.join(schema.metrics) if schema.metrics else DEFAULT_PENDING_TEXT}",
                f"- Main results: {schema.main_results or DEFAULT_PENDING_TEXT}",
                "",
            ])

        lines.extend(["## Cross-Paper Summary", (compare_result.cross_paper_summary if compare_result else "No comparison summary available."), ""])
        if compare_result and compare_result.method_comparison:
            lines.append("## Method Comparison")
            for item in compare_result.method_comparison:
                lines.append(f"- {item}")
            lines.append("")
        lines.append("## Discussion Directions")
        if gap_candidates:
            for gap in gap_candidates:
                lines.append(f"- {gap.statement} [{gap.validation_result}]")
        else:
            lines.append("- No validated discussion directions are available yet.")
        return "\n".join(lines)

    def _build_survey_export(self, topic: str, paper_schemas: list[PaperSchema], compare_result: CompareResult | None, gap_candidates: list[GapCandidate], focus_dimensions: list[str] | None, user_requirements: str) -> str:
        lines = ["# Survey Draft", "", f"Topic: {topic or 'Not specified'}", ""]
        lines.extend(self._preference_block(focus_dimensions, user_requirements))
        lines.append("## Research Landscape")
        lines.append(compare_result.cross_paper_summary if compare_result else "No cross-paper summary is available yet.")
        lines.append("")
        if compare_result and compare_result.method_comparison:
            lines.append("## Method Comparison")
            for item in compare_result.method_comparison:
                lines.append(f"- {item}")
            lines.append("")
        lines.append("## Paper Notes")
        for schema in paper_schemas:
            lines.append(
                f"{schema.title} studies {schema.research_problem or 'an unspecified problem'} using {schema.method or 'an unspecified method'} on {', '.join(schema.datasets) if schema.datasets else 'unspecified datasets'}, reporting {schema.main_results or 'pending main results'}."
            )
            if schema.limitations:
                lines.append(f"Key limitations: {'; '.join(schema.limitations[:2])}.")
            lines.append("")
        lines.append("## Limitations and Future Directions")
        if compare_result and compare_result.limitations_summary:
            lines.append(compare_result.limitations_summary)
        if gap_candidates:
            for gap in gap_candidates:
                lines.append(f"- {gap.statement} [{gap.validation_result}]")
        else:
            lines.append("- No validated future direction is available yet.")
        return "\n".join(lines)

    def _build_gap_analysis_export(self, topic: str, compare_result: CompareResult | None, gap_candidates: list[GapCandidate], focus_dimensions: list[str] | None, user_requirements: str) -> str:
        lines = ["# Gap Analysis", "", f"Topic: {topic or 'Not specified'}", ""]
        lines.extend(self._preference_block(focus_dimensions, user_requirements))
        if compare_result:
            lines.extend(["## Cross-Paper Summary", compare_result.cross_paper_summary or compare_result.trend_summary, ""])
        lines.append("## Final Gap Candidates")
        if not gap_candidates:
            lines.append("No confirmed or likely gap is available yet.")
        for gap in gap_candidates:
            lines.extend([
                f"### {gap.statement}",
                f"- Validation result: {gap.validation_result}",
                f"- Validation level: {gap.validation_level}",
                f"- Confidence: {gap.confidence}",
                f"- Coverage: {gap.coverage_count} paper(s) / {gap.coverage_status or 'n/a'}",
                f"- Support strength: {gap.support_strength or 'n/a'}",
                f"- Counter strength: {gap.counter_strength or 'n/a'}",
                f"- Validation reason: {gap.validation_reason or DEFAULT_PENDING_TEXT}",
                f"- Suggested direction: {gap.suggested_direction or DEFAULT_PENDING_TEXT}",
                f"- Human review: {'yes' if gap.requires_human_review else 'no'}{f' ({gap.human_review_reason})' if gap.human_review_reason else ''}",
                "- Supporting evidence:",
            ])
            if gap.supporting_evidence:
                for evidence in gap.supporting_evidence[:3]:
                    lines.append(f"  - p.{evidence.page_start}-{evidence.page_end} {evidence.content[:120]}")
            else:
                lines.append("  - No supporting evidence retained.")
            lines.append("- Counter evidence:")
            if gap.counter_evidence:
                for evidence in gap.counter_evidence[:3]:
                    lines.append(f"  - p.{evidence.page_start}-{evidence.page_end} {evidence.content[:120]}")
            else:
                lines.append("  - No counter evidence retained.")
            if gap.coverage_risks:
                lines.append(f"- Coverage risks: {'; '.join(gap.coverage_risks)}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _load_prompt_template() -> str:
        prompt_path = PROMPTS_DIR / "generate_output_prompt.txt"
        if prompt_path.exists():
            try:
                return prompt_path.read_text(encoding="utf-8").strip()
            except UnicodeDecodeError:
                return prompt_path.read_text(encoding="gbk").strip()
        return "You are a final output generation assistant for research tasks."
