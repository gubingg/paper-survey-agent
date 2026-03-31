from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

import requests

from app.schemas.gap_schema import GapCandidate
from app.schemas.paper_schema import CompareMatrixRow, CompareResult, PaperSchema
from app.services.gap_service import GapService
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

logger = get_logger(__name__)
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


class CompareService:
    """Skill-aligned service for cross-paper comparison and raw gap generation."""

    def __init__(self) -> None:
        self.gap_service = GapService()
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.model_name = os.getenv("QWEN_MODEL_NAME", "qwen3-max")
        self.base_url = os.getenv(
            "QWEN_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        )
        self.timeout = int(os.getenv("QWEN_TIMEOUT", "180"))
        self.prompt_template = self._load_prompt_template()

    def build_compare_result(
        self,
        paper_schemas: list[PaperSchema],
        topic: str = "",
        focus_dimensions: list[str] | None = None,
        user_requirements: str = "",
    ) -> CompareResult:
        """Generate a comparison matrix and a lightweight trend summary."""

        heuristic_result = self._build_heuristic_compare_result(
            paper_schemas,
            topic=topic,
            focus_dimensions=focus_dimensions,
            user_requirements=user_requirements,
        )
        if not self.api_key or not heuristic_result.rows:
            return heuristic_result

        try:
            llm_fields = self._build_compare_result_with_llm(
                heuristic_result.rows,
                topic=topic,
                focus_dimensions=focus_dimensions,
                user_requirements=user_requirements,
            )
        except Exception as exc:
            logger.warning("Compare LLM generation failed, falling back to heuristic summary: %s", exc)
            return heuristic_result

        return heuristic_result.model_copy(
            update={
                "trend_summary": llm_fields.get("cross_paper_summary") or heuristic_result.trend_summary,
                "cross_paper_summary": llm_fields.get("cross_paper_summary") or heuristic_result.cross_paper_summary,
                "method_comparison": llm_fields.get("method_comparison") or heuristic_result.method_comparison,
                "limitations_summary": llm_fields.get("limitations_summary") or heuristic_result.limitations_summary,
                "method_categories": llm_fields.get("method_categories") or heuristic_result.method_categories,
                "dataset_trends": llm_fields.get("dataset_trends") or heuristic_result.dataset_trends,
                "metric_trends": llm_fields.get("metric_trends") or heuristic_result.metric_trends,
            }
        )

    def _build_heuristic_compare_result(
        self,
        paper_schemas: list[PaperSchema],
        topic: str = "",
        focus_dimensions: list[str] | None = None,
        user_requirements: str = "",
    ) -> CompareResult:
        rows = [
            CompareMatrixRow(
                paper_id=schema.paper_id,
                title=schema.title,
                research_problem=schema.research_problem,
                method=schema.method,
                datasets=schema.datasets,
                metrics=schema.metrics,
                limitations=schema.limitations,
            )
            for schema in paper_schemas
        ]

        method_categories = [schema.method_category for schema in paper_schemas if schema.method_category]
        method_counter = Counter(method_categories)
        dataset_counter = Counter(item for schema in paper_schemas for item in schema.datasets)
        metric_counter = Counter(item for schema in paper_schemas for item in schema.metrics)
        limitation_counter = Counter(item for schema in paper_schemas for item in schema.limitations)

        summary_parts: list[str] = []
        if topic:
            summary_parts.append(f"Topic: {topic}.")
        if focus_dimensions:
            focus_labels = [FOCUS_DIMENSION_LABELS.get(item, item) for item in focus_dimensions]
            summary_parts.append(f"Focus dimensions: {', '.join(focus_labels)}.")
        if user_requirements.strip():
            summary_parts.append(f"User requirements: {user_requirements.strip()}.")
        if method_counter:
            top_methods = ", ".join(name for name, _ in method_counter.most_common(4))
            summary_parts.append(f"Common method families include {top_methods}.")
        if dataset_counter:
            top_datasets = ", ".join(name for name, _ in dataset_counter.most_common(5))
            summary_parts.append(f"Frequently used datasets include {top_datasets}.")
        if metric_counter:
            top_metrics = ", ".join(name for name, _ in metric_counter.most_common(5))
            summary_parts.append(f"Common evaluation metrics include {top_metrics}.")
        if limitation_counter:
            top_limitations = "; ".join(name for name, _ in limitation_counter.most_common(3))
            summary_parts.append(f"Recurring limitations include {top_limitations}.")
        if not summary_parts:
            summary_parts.append("Cross-paper comparison is available after at least one structured paper schema is extracted.")

        cross_paper_summary = " ".join(summary_parts)
        method_comparison = [f"{name}: {count} paper(s)" for name, count in method_counter.most_common(5)]
        limitations_summary = (
            "; ".join(name for name, _ in limitation_counter.most_common(5))
            if limitation_counter
            else "No repeated limitations were extracted across the current paper set."
        )

        return CompareResult(
            rows=rows,
            trend_summary=cross_paper_summary,
            cross_paper_summary=cross_paper_summary,
            method_comparison=method_comparison,
            limitations_summary=limitations_summary,
            method_categories=[name for name, _ in method_counter.most_common(5)],
            dataset_trends=[name for name, _ in dataset_counter.most_common(5)],
            metric_trends=[name for name, _ in metric_counter.most_common(5)],
        )

    def _build_compare_result_with_llm(
        self,
        rows: list[CompareMatrixRow],
        *,
        topic: str,
        focus_dimensions: list[str] | None,
        user_requirements: str,
    ) -> dict:
        focus_labels = [FOCUS_DIMENSION_LABELS.get(item, item) for item in (focus_dimensions or [])]
        prompt = (
            f"{self.prompt_template}\n\n"
            "Understand the user requirements before deciding the comparison emphasis and ordering. "
            "Return valid JSON with keys: cross_paper_summary, method_comparison, limitations_summary, method_categories, dataset_trends, metric_trends. "
            "The last four keys must be string arrays.\n\n"
            f"Topic: {topic or 'Not specified'}\n"
            f"Focus dimensions: {', '.join(focus_labels) if focus_labels else 'Not specified'}\n"
            f"User requirements: {user_requirements.strip() or 'None'}\n\n"
            f"Paper rows JSON:\n{json.dumps([row.model_dump() for row in rows], ensure_ascii=False)}"
        )
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a cross-paper comparison assistant. Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(self.base_url, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        return {
            "cross_paper_summary": str(data.get("cross_paper_summary") or "").strip(),
            "method_comparison": [str(item).strip() for item in data.get("method_comparison", []) if str(item).strip()],
            "limitations_summary": str(data.get("limitations_summary") or "").strip(),
            "method_categories": [str(item).strip() for item in data.get("method_categories", []) if str(item).strip()],
            "dataset_trends": [str(item).strip() for item in data.get("dataset_trends", []) if str(item).strip()],
            "metric_trends": [str(item).strip() for item in data.get("metric_trends", []) if str(item).strip()],
        }

    @staticmethod
    def _load_prompt_template() -> str:
        prompt_path = PROMPTS_DIR / "compare_prompt.txt"
        if prompt_path.exists():
            try:
                return prompt_path.read_text(encoding="utf-8").strip()
            except UnicodeDecodeError:
                return prompt_path.read_text(encoding="gbk").strip()
        return "You are a paper comparison assistant."

    def generate_gap_candidates_raw(
        self,
        project_id: str,
        paper_schemas: list[PaperSchema],
        compare_result: CompareResult | None,
        focus_dimensions: list[str] | None = None,
        user_requirements: str = "",
    ) -> list[GapCandidate]:
        """Produce raw gap candidates from cross-paper comparison signals."""

        return self.gap_service.generate_gap_candidates(
            project_id=project_id,
            paper_schemas=paper_schemas,
            compare_result=compare_result,
            focus_dimensions=focus_dimensions,
            user_requirements=user_requirements,
        )
