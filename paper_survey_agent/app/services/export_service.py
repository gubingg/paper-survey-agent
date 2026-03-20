from __future__ import annotations

from app.schemas.gap_schema import GapCandidate
from app.schemas.paper_schema import CompareResult, ExportPayload, PaperSchema
from app.utils.file_utils import export_text_file


class ExportService:
    """Service for project exports used by Streamlit and API consumers."""

    def export(
        self,
        project_id: str,
        export_type: str,
        topic: str,
        paper_schemas: list[PaperSchema],
        compare_result: CompareResult | None,
        gap_candidates: list[GapCandidate],
    ) -> ExportPayload:
        """Generate an export payload and persist it under data/exports."""

        normalized_type = self._normalize_export_type(export_type)
        if normalized_type == "compare_table":
            content = self._build_compare_table(compare_result)
        elif normalized_type == "survey":
            content = self._build_survey_export(topic, paper_schemas, compare_result)
        elif normalized_type == "gap_analysis":
            content = self._build_gap_analysis_export(topic, compare_result, gap_candidates)
        else:
            content = self._build_meeting_outline(topic, paper_schemas, compare_result, gap_candidates)

        file_path = export_text_file(project_id, normalized_type, content)
        return ExportPayload(export_type=normalized_type, content=content, file_path=file_path)

    @staticmethod
    def _normalize_export_type(export_type: str) -> str:
        if export_type == "related_work_markdown":
            return "survey"
        return export_type

    @staticmethod
    def _build_compare_table(compare_result: CompareResult | None) -> str:
        if compare_result is None or not compare_result.rows:
            return "# Compare Table\n\n暂无可导出的对比结果。"

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

    @staticmethod
    def _build_meeting_outline(
        topic: str,
        paper_schemas: list[PaperSchema],
        compare_result: CompareResult | None,
        gap_candidates: list[GapCandidate],
    ) -> str:
        lines = [
            "# Meeting Outline",
            "",
            "## 研究背景",
            topic or "待补充研究主题。",
            "",
            "## 代表工作",
        ]
        for index, schema in enumerate(paper_schemas, start=1):
            lines.extend(
                [
                    f"### {index}. {schema.title}",
                    f"- 研究问题：{schema.research_problem or '待补充'}",
                    f"- 方法：{schema.method or '待补充'}",
                    f"- 数据集：{', '.join(schema.datasets) if schema.datasets else '待补充'}",
                    f"- 指标：{', '.join(schema.metrics) if schema.metrics else '待补充'}",
                    f"- 可展示亮点：{schema.main_results or '待补充'}",
                    "",
                ]
            )

        lines.extend(["## 对比总结", compare_result.trend_summary if compare_result else "暂无总结。", ""])
        lines.append("## 候选 Research Gaps")
        for gap in gap_candidates:
            lines.append(f"- {gap.statement} [{gap.validation_result or '待验证'}]")
        if not gap_candidates:
            lines.append("- 暂无候选研究空白。")
        return "\n".join(lines)

    @staticmethod
    def _build_survey_export(topic: str, paper_schemas: list[PaperSchema], compare_result: CompareResult | None) -> str:
        lines = ["# Survey Draft", "", f"研究主题：{topic or '未设置'}", "", "## 方法脉络"]
        if compare_result:
            lines.extend([compare_result.trend_summary, ""])
        for schema in paper_schemas:
            lines.append(
                f"{schema.title} 聚焦于 {schema.research_problem or '相关问题'}，"
                f"采用 {schema.method or '相应方法'}，"
                f"在 {', '.join(schema.datasets) if schema.datasets else '若干数据集'} 上进行评估，"
                f"主要结果为 {schema.main_results or '待补充'}。"
            )
            if schema.limitations:
                lines.append(f"局限：{'；'.join(schema.limitations[:2])}。")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _build_gap_analysis_export(topic: str, compare_result: CompareResult | None, gap_candidates: list[GapCandidate]) -> str:
        lines = ["# Gap Analysis", "", f"研究主题：{topic or '未设置'}", ""]
        if compare_result:
            lines.extend(["## 多论文对比摘要", compare_result.trend_summary, ""])
        lines.append("## 候选研究空白验证结果")
        if not gap_candidates:
            lines.append("暂无候选研究空白。")
        for gap in gap_candidates:
            lines.extend(
                [
                    f"### {gap.statement}",
                    f"- 最终判断：{gap.validation_result or '待验证'}",
                    f"- 置信度：{gap.confidence}",
                    f"- 覆盖论文数：{gap.coverage_count}",
                    f"- 是否需人工确认：{'是' if gap.requires_human_review else '否'}",
                    f"- 建议方向：{gap.suggested_direction or '待补充'}",
                    "- 支持证据：",
                ]
            )
            for evidence in gap.supporting_evidence[:3]:
                lines.append(f"  - p.{evidence.page_start}-{evidence.page_end} {evidence.content[:120]}")
            lines.append("- 反证/冲突证据：")
            for evidence in gap.counter_evidence[:3]:
                lines.append(f"  - p.{evidence.page_start}-{evidence.page_end} {evidence.content[:120]}")
            lines.append("")
        return "\n".join(lines)
