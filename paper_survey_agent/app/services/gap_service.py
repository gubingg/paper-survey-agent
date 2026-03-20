from __future__ import annotations

import re
from collections import Counter

from app.schemas.agent_schema import EvidenceSnippet
from app.schemas.gap_schema import GapCandidate
from app.schemas.paper_schema import CompareResult, PaperSchema


class GapService:
    """Service for initial gap candidate generation."""

    def generate_gap_candidates(
        self,
        project_id: str,
        paper_schemas: list[PaperSchema],
        compare_result: CompareResult | None,
    ) -> list[GapCandidate]:
        """Generate preliminary gap candidates before the validation agent runs."""

        if not paper_schemas:
            return []

        candidates: list[GapCandidate] = []
        limitation_counter = Counter(
            limitation.strip()
            for schema in paper_schemas
            for limitation in schema.limitations
            if limitation.strip()
        )
        dataset_counter = Counter(dataset for schema in paper_schemas for dataset in schema.datasets)
        metric_counter = Counter(metric for schema in paper_schemas for metric in schema.metrics)

        if limitation_counter:
            top_limitation, frequency = limitation_counter.most_common(1)[0]
            candidates.append(
                GapCandidate(
                    gap_id=f"gap_{project_id[-4:]}_limitation",
                    project_id=project_id,
                    statement=f"现有工作反复暴露出 '{top_limitation}'，说明该方向仍存在待解决的稳定性或适用性问题。",
                    supporting_papers=[schema.paper_id for schema in paper_schemas if top_limitation in schema.limitations],
                    evidence_summary=[f"共有 {frequency} 篇论文提到相似局限。"],
                    suggested_direction="围绕该局限设计更有针对性的改进方案与误差分析。",
                    status="pending",
                )
            )

        if len(dataset_counter) <= 2 and dataset_counter:
            dataset_names = ", ".join(name for name, _ in dataset_counter.most_common(3))
            candidates.append(
                GapCandidate(
                    gap_id=f"gap_{project_id[-4:]}_dataset",
                    project_id=project_id,
                    statement="现有论文的数据集覆盖面偏窄，跨场景泛化能力仍缺乏充分验证。",
                    supporting_papers=[schema.paper_id for schema in paper_schemas if schema.datasets],
                    evidence_summary=[f"当前实验主要集中在 {dataset_names}。"],
                    suggested_direction="扩展到更多语言、场景或真实数据环境进行验证。",
                    status="pending",
                )
            )

        if len(metric_counter) <= 2 and metric_counter:
            metric_names = ", ".join(name for name, _ in metric_counter.most_common(3))
            candidates.append(
                GapCandidate(
                    gap_id=f"gap_{project_id[-4:]}_metric",
                    project_id=project_id,
                    statement="当前评测指标较为单一，尚不足以全面反映方法在真实研究场景中的综合表现。",
                    supporting_papers=[schema.paper_id for schema in paper_schemas if schema.metrics],
                    evidence_summary=[f"多数论文只报告 {metric_names} 等有限指标。"],
                    suggested_direction="增加鲁棒性、效率、成本和可解释性等多维评测。",
                    status="pending",
                )
            )

        if not candidates and compare_result is not None:
            candidates.append(
                GapCandidate(
                    gap_id=f"gap_{project_id[-4:]}_general",
                    project_id=project_id,
                    statement="现有论文之间仍缺少统一、系统的实验对照，因此研究结论的可比性不足。",
                    supporting_papers=[row.paper_id for row in compare_result.rows],
                    evidence_summary=[compare_result.trend_summary],
                    suggested_direction="建立统一实验设置并补充消融、跨任务和跨数据集比较。",
                    status="pending",
                )
            )

        return candidates[:3]

    @staticmethod
    def extract_gap_keywords(statement: str) -> list[str]:
        """Extract keywords from a gap statement for retrieval use."""

        return [token for token in re.findall(r"[A-Za-z\u4e00-\u9fff0-9\-]+", statement.lower()) if len(token) > 1][:10]
