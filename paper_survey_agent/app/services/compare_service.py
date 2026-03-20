from __future__ import annotations

from collections import Counter

from app.schemas.paper_schema import CompareMatrixRow, CompareResult, PaperSchema


class CompareService:
    """Service for building comparison tables and trend summaries."""

    def build_compare_result(self, paper_schemas: list[PaperSchema], topic: str = "") -> CompareResult:
        """Generate a comparison matrix and a lightweight trend summary."""

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
        dataset_counter = Counter(item for schema in paper_schemas for item in schema.datasets)
        metric_counter = Counter(item for schema in paper_schemas for item in schema.metrics)
        limitation_counter = Counter(item for schema in paper_schemas for item in schema.limitations)

        summary_parts: list[str] = []
        if topic:
            summary_parts.append(f"研究主题聚焦于 {topic}。")
        if method_categories:
            top_methods = ", ".join(name for name, _ in Counter(method_categories).most_common(4))
            summary_parts.append(f"方法类别主要包括 {top_methods}。")
        if dataset_counter:
            top_datasets = ", ".join(name for name, _ in dataset_counter.most_common(5))
            summary_parts.append(f"常见数据集包括 {top_datasets}。")
        if metric_counter:
            top_metrics = ", ".join(name for name, _ in metric_counter.most_common(5))
            summary_parts.append(f"常见评测指标包括 {top_metrics}。")
        if limitation_counter:
            top_limitations = "；".join(name for name, _ in limitation_counter.most_common(3))
            summary_parts.append(f"重复出现的局限主要集中在 {top_limitations}。")
        if not summary_parts:
            summary_parts.append("当前论文数量较少，趋势总结会随着更多论文上传而逐步稳定。")

        return CompareResult(
            rows=rows,
            trend_summary=" ".join(summary_parts),
            method_categories=[name for name, _ in Counter(method_categories).most_common(5)],
            dataset_trends=[name for name, _ in dataset_counter.most_common(5)],
            metric_trends=[name for name, _ in metric_counter.most_common(5)],
        )
