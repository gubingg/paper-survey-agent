from __future__ import annotations

from collections import Counter

from app.schemas.agent_schema import EvidenceSnippet
from app.schemas.gap_schema import GapCandidate
from app.schemas.paper_schema import CompareResult, PaperChunk, PaperSchema
from app.services.gap_service import GapService


class GapValidationService:
    """Business logic used by the research gap validation agent."""

    def __init__(self) -> None:
        self.gap_service = GapService()

    def decompose_gap(self, candidate: GapCandidate) -> list[str]:
        """Split a gap statement into lightweight validation points."""

        keywords = self.gap_service.extract_gap_keywords(candidate.statement)
        points = [candidate.statement]
        if keywords:
            points.append(" ".join(keywords[:4]))
        if candidate.suggested_direction:
            points.append(candidate.suggested_direction)
        return points[:3]

    @staticmethod
    def check_coverage(evidences: list[EvidenceSnippet]) -> int:
        """Count how many distinct papers are covered by evidence."""

        return len({item.paper_id for item in evidences})

    def judge_gap_evidence(
        self,
        supporting_evidence: list[EvidenceSnippet],
        counter_evidence: list[EvidenceSnippet],
        coverage_count: int,
    ) -> tuple[str, float, bool]:
        """Map evidence into one of the four required validation labels."""

        support_score = sum(item.score for item in supporting_evidence)
        counter_score = sum(item.score for item in counter_evidence)

        if support_score <= 0.01 and counter_score > 0.01:
            return "不成立", 0.2, True
        if counter_score > support_score * 0.7 and counter_score > 0.01:
            return "有冲突", 0.45, True
        if coverage_count >= 2 and support_score > 0.02:
            requires_human_review = coverage_count < 3 or len(supporting_evidence) <= 2
            return "成立", min(0.85, 0.45 + 0.1 * coverage_count), requires_human_review
        return "证据弱", 0.35, True

    def build_counter_queries(self, candidate: GapCandidate) -> list[str]:
        """Generate queries intended to find conflict evidence."""

        return [
            f"counter example {candidate.statement}",
            f"opposite evidence {candidate.statement}",
        ]

    @staticmethod
    def attach_validation(candidate: GapCandidate, supporting: list[EvidenceSnippet], counter: list[EvidenceSnippet], coverage_count: int, validation_result: str, confidence: float, requires_human_review: bool) -> GapCandidate:
        """Attach validation evidence to the candidate."""

        candidate.supporting_evidence = supporting
        candidate.counter_evidence = counter
        candidate.coverage_count = coverage_count
        candidate.validation_result = validation_result
        candidate.confidence = confidence
        candidate.requires_human_review = requires_human_review
        if not candidate.evidence_summary:
            candidate.evidence_summary = []
        candidate.evidence_summary = [
            *candidate.evidence_summary[:2],
            f"支持证据 {len(supporting)} 条，反证 {len(counter)} 条，覆盖 {coverage_count} 篇论文。",
            f"验证结果：{validation_result}",
        ]
        return candidate

    def collect_counter_evidence_from_schemas(self, candidate: GapCandidate, paper_schemas: list[PaperSchema]) -> list[EvidenceSnippet]:
        """Build coarse counter evidence from schema-level contradictions."""

        statement = candidate.statement.lower()
        counter: list[EvidenceSnippet] = []
        if "数据集" in candidate.statement or "dataset" in statement:
            for schema in paper_schemas:
                if len(schema.datasets) >= 3:
                    counter.append(
                        EvidenceSnippet(
                            paper_id=schema.paper_id,
                            content=f"{schema.title} 使用了多个数据集：{', '.join(schema.datasets[:4])}",
                            score=0.03,
                        )
                    )
        if "指标" in candidate.statement or "metric" in statement:
            for schema in paper_schemas:
                if len(schema.metrics) >= 3:
                    counter.append(
                        EvidenceSnippet(
                            paper_id=schema.paper_id,
                            content=f"{schema.title} 报告了多个评测指标：{', '.join(schema.metrics[:4])}",
                            score=0.03,
                        )
                    )
        if "局限" in candidate.statement or "问题" in candidate.statement:
            for schema in paper_schemas:
                if schema.strengths:
                    counter.append(
                        EvidenceSnippet(
                            paper_id=schema.paper_id,
                            content=f"{schema.title} 强调优势：{schema.strengths[0]}",
                            score=0.02,
                        )
                    )
        return counter[:4]
