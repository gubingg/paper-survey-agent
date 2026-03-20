from __future__ import annotations

import re
from collections import Counter

from app.schemas.agent_schema import EvidenceSnippet, FieldCompletionResult, FieldProblem
from app.schemas.paper_schema import PaperChunk, PaperSchema


class FieldCompletionService:
    """Business logic used by the field completion agent subgraph."""

    FOCUS_FIELDS = ("datasets", "metrics", "limitations", "future_work")
    UNKNOWN_MARKERS = {"n/a", "na", "unknown", "not mentioned", "未提及", "未知", "none"}

    def detect_problem_fields(self, paper_schema: PaperSchema) -> list[FieldProblem]:
        """Detect suspicious fields that may need completion."""

        problems: list[FieldProblem] = []
        for field_name in self.FOCUS_FIELDS:
            value = getattr(paper_schema, field_name)
            reason = self._detect_problem_reason(value)
            if reason:
                severity = "high" if field_name in {"limitations", "future_work"} else "medium"
                problems.append(
                    FieldProblem(
                        paper_id=paper_schema.paper_id,
                        field_name=field_name,
                        current_value=value,
                        reason=reason,
                        severity=severity,
                    )
                )
        return problems

    def judge_need_fill(self, current_value: str | list[str]) -> tuple[bool, str]:
        """Decide whether a field really needs completion."""

        reason = self._detect_problem_reason(current_value)
        return (reason is not None, reason or "信息完整")

    def build_retrieval_query(self, field_name: str, current_value: str | list[str]) -> str:
        """Construct a targeted retrieval query for internal evidence search."""

        base_queries = {
            "datasets": "dataset benchmark evaluation data experiments",
            "metrics": "metric evaluation ndcg recall precision f1 auc",
            "limitations": "limitation challenge drawback however discussion",
            "future_work": "future work can be extended in future improve next step",
        }
        serialized = self._serialize_value(current_value)
        return f"{field_name} {base_queries.get(field_name, field_name)} {serialized}".strip()

    @staticmethod
    def judge_evidence(field_name: str, evidences: list[EvidenceSnippet]) -> bool:
        """Judge whether retrieved evidence is strong enough."""

        if not evidences:
            return False
        if field_name in {"datasets", "metrics"}:
            return len(evidences) >= 1 and max(item.score for item in evidences) >= 0.01
        return len(evidences) >= 2 or sum(item.score for item in evidences) >= 0.03

    def refine_query(self, field_name: str, retry_count: int) -> str:
        """Create a retry query for another evidence attempt."""

        retry_terms = {
            1: {
                "datasets": "experiments benchmark corpus",
                "metrics": "evaluation metric performance table",
                "limitations": "however limitation drawback",
                "future_work": "future work discussion conclusion",
            },
            2: {
                "datasets": "dataset experimental setup",
                "metrics": "results metric score",
                "limitations": "challenge failure case",
                "future_work": "next step extension",
            },
        }
        return retry_terms.get(retry_count, {}).get(field_name, field_name)

    def generate_filled_value(self, field_name: str, evidences: list[EvidenceSnippet], current_value: str | list[str]) -> tuple[str | list[str], str]:
        """Generate a completed field value from internal evidence."""

        if not evidences:
            fallback = "证据不足" if field_name in {"limitations", "future_work"} else ["证据不足"]
            return fallback, "evidence_insufficient"

        if field_name == "datasets":
            items = self._extract_named_items(evidences, ["dataset", "benchmark", "corpus"])
            if items:
                return items, "filled"
            return ["未明确提及"], "not_mentioned"

        if field_name == "metrics":
            items = self._extract_metric_items(evidences)
            if items:
                return items, "filled"
            return ["未明确提及"], "not_mentioned"

        sentences = self._extract_relevant_sentences(evidences, field_name)
        if sentences:
            return sentences[:3], "filled"
        fallback_text = "未明确提及" if self._serialize_value(current_value).strip() == "" else "证据不足"
        return [fallback_text], "not_mentioned" if fallback_text == "未明确提及" else "evidence_insufficient"

    @staticmethod
    def requires_human_review(field_name: str, evidences: list[EvidenceSnippet], fill_status: str) -> bool:
        """Flag high-risk fill results for human review."""

        if fill_status != "filled":
            return True
        if field_name in {"limitations", "future_work"}:
            return True
        return len(evidences) <= 1

    def apply_completion_to_schema(self, schema: PaperSchema, result: FieldCompletionResult) -> PaperSchema:
        """Apply a completion result to a paper schema."""

        value = result.filled_value
        if isinstance(getattr(schema, result.field_name), list):
            setattr(schema, result.field_name, value if isinstance(value, list) else [str(value)])
        else:
            setattr(schema, result.field_name, value if isinstance(value, str) else "；".join(value))

        if result.requires_human_review and "字段补全结果需要人工确认。" not in schema.warnings:
            schema.warnings.append("字段补全结果需要人工确认。")
            schema.needs_review = True
        return schema

    def result_from_state(
        self,
        paper_id: str,
        field_name: str,
        original_value: str | list[str],
        need_fill: bool,
        retrieval_query: str,
        evidences: list[EvidenceSnippet],
        retry_count: int,
        filled_value: str | list[str],
        fill_status: str,
        requires_human_review: bool,
        logs: list[str],
    ) -> FieldCompletionResult:
        """Build the persisted completion result model."""

        return FieldCompletionResult(
            paper_id=paper_id,
            field_name=field_name,
            original_value=original_value,
            filled_value=filled_value,
            need_fill=need_fill,
            retrieval_query=retrieval_query,
            candidate_evidence=evidences,
            retry_count=retry_count,
            fill_status=fill_status,
            requires_human_review=requires_human_review,
            review_status="pending" if requires_human_review else "approved",
            logs=logs,
        )

    def _detect_problem_reason(self, value: str | list[str]) -> str | None:
        serialized = self._serialize_value(value).strip().lower()
        if serialized == "":
            return "字段为空"
        if serialized in self.UNKNOWN_MARKERS:
            return "字段为未知或未提及"
        if len(serialized) < 8:
            return "字段内容过短"
        return None

    @staticmethod
    def _serialize_value(value: str | list[str]) -> str:
        if isinstance(value, list):
            return " ".join(str(item) for item in value if str(item).strip())
        return str(value or "")

    @staticmethod
    def _extract_named_items(evidences: list[EvidenceSnippet], hints: list[str]) -> list[str]:
        items: list[str] = []
        for evidence in evidences:
            for sentence in re.split(r"(?<=[.!?。；])\s+", evidence.content):
                lower_sentence = sentence.lower()
                if any(hint in lower_sentence for hint in hints):
                    items.extend(re.findall(r"\b[A-Z][A-Za-z0-9\-]{2,}\b", sentence))
        deduped: list[str] = []
        seen: set[str] = set()
        for item in items:
            normalized = item.strip()
            if normalized and normalized.lower() not in seen:
                seen.add(normalized.lower())
                deduped.append(normalized)
        return deduped[:6]

    @staticmethod
    def _extract_metric_items(evidences: list[EvidenceSnippet]) -> list[str]:
        vocabulary = ["accuracy", "precision", "recall", "f1", "auc", "ndcg", "map", "mrr", "rmse", "mae", "bleu", "rouge"]
        found: list[str] = []
        for evidence in evidences:
            lower_content = evidence.content.lower()
            found.extend(metric.upper() if len(metric) <= 4 else metric for metric in vocabulary if metric in lower_content)
        counts = Counter(found)
        return [metric for metric, _ in counts.most_common(6)]

    @staticmethod
    def _extract_relevant_sentences(evidences: list[EvidenceSnippet], field_name: str) -> list[str]:
        markers = {
            "limitations": ["however", "limitation", "challenge", "drawback", "cost"],
            "future_work": ["future work", "in future", "can be extended", "next step", "improve"],
        }
        matched: list[str] = []
        for evidence in evidences:
            for sentence in re.split(r"(?<=[.!?。；])\s+", evidence.content):
                if any(marker in sentence.lower() for marker in markers.get(field_name, [])):
                    cleaned = sentence.strip()
                    if cleaned:
                        matched.append(cleaned)
        return matched
