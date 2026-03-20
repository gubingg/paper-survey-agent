from __future__ import annotations

import json
import os
import re
import time

import requests

from app.schemas.paper_schema import PaperSchema, ParsedPaper
from app.utils.chunk_utils import extract_keywords_from_text, extract_year, normalize_text_list
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ExtractionService:
    """Service that extracts a normalized paper card from parsed paper text."""

    def __init__(self) -> None:
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.model_name = os.getenv("QWEN_MODEL_NAME", "qwen3-max")
        self.high_quality_model = os.getenv("QWEN_MAX_MODEL_NAME", "qwen3-max")
        self.base_url = os.getenv(
            "QWEN_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        )
        self.timeout = int(os.getenv("QWEN_TIMEOUT", "180"))
        self.max_retries = int(os.getenv("QWEN_RETRIES", "2"))

    def extract_paper_schema(self, parsed_paper: ParsedPaper, use_high_quality: bool = False) -> PaperSchema:
        """Extract a structured paper card, preferring LLM output if configured."""

        if self.api_key:
            model = self.high_quality_model if use_high_quality else self.model_name
            llm_result = self._extract_with_llm(parsed_paper, model=model)
            if llm_result is not None:
                return llm_result
        return self._heuristic_extract(parsed_paper)

    def _extract_with_llm(self, parsed_paper: ParsedPaper, model: str) -> PaperSchema | None:
        """Try to call a Qwen-compatible structured extraction endpoint with retries."""

        schema_json = json.dumps(PaperSchema.model_json_schema(), ensure_ascii=False)
        content_budget = 16000
        for attempt in range(1, self.max_retries + 1):
            prompt = (
                "You are extracting a paper card for literature review. "
                "Return valid JSON only, matching the provided schema exactly.\n\n"
                f"Schema:\n{schema_json}\n\n"
                f"Paper ID: {parsed_paper.paper_id}\n"
                f"Title Guess: {parsed_paper.title_guess}\n\n"
                f"Paper Content:\n{parsed_paper.full_text[:content_budget]}"
            )
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You output strict JSON for paper extraction."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            try:
                response = requests.post(self.base_url, headers=headers, json=payload, timeout=self.timeout)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                data = json.loads(content)
                data["paper_id"] = parsed_paper.paper_id
                return PaperSchema.model_validate(data)
            except Exception as exc:
                logger.warning(
                    "LLM extraction attempt %s/%s failed for %s: %s",
                    attempt,
                    self.max_retries,
                    parsed_paper.paper_id,
                    exc,
                )
                content_budget = max(8000, content_budget - 3000)
                if attempt < self.max_retries:
                    time.sleep(1.2 * attempt)
        return None

    def _heuristic_extract(self, parsed_paper: ParsedPaper) -> PaperSchema:
        """Fallback extraction that keeps the MVP runnable without external APIs."""

        sections = self._collect_section_text(parsed_paper)
        abstract_intro = self._join_sections(sections, ["abstract", "introduction", "unknown"])
        method_text = self._join_sections(sections, ["method", "unknown"])
        experiment_text = self._join_sections(sections, ["experiments", "unknown"])
        conclusion_text = self._join_sections(sections, ["conclusion", "unknown"])

        title = parsed_paper.title_guess or f"Paper {parsed_paper.paper_id}"
        year = extract_year(parsed_paper.full_text)
        datasets = self._extract_named_items(parsed_paper.full_text, ["dataset", "datasets", "benchmark"])
        metrics = self._extract_metrics(parsed_paper.full_text)
        limitations = self._extract_sentences(parsed_paper.full_text, ["limitation", "however", "challenge", "future work"])
        future_work = self._extract_sentences(
            conclusion_text or parsed_paper.full_text,
            ["future work", "in the future", "we plan", "can be extended"],
        )
        warnings: list[str] = []

        if not datasets:
            warnings.append("数据集信息未被稳定提取，当前结果来自启发式抽取。")
        if not metrics:
            warnings.append("评测指标未被稳定提取，当前结果来自启发式抽取。")

        return PaperSchema(
            paper_id=parsed_paper.paper_id,
            title=title,
            year=year,
            research_problem=self._summarize_section(abstract_intro, fallback=parsed_paper.full_text),
            method=self._summarize_section(method_text, fallback=parsed_paper.full_text),
            method_category=self._infer_method_category(method_text or parsed_paper.full_text),
            datasets=datasets,
            metrics=metrics,
            main_results=self._summarize_section(experiment_text, fallback=parsed_paper.full_text),
            strengths=self._infer_strengths(method_text or parsed_paper.full_text, metrics),
            limitations=limitations[:5],
            future_work=future_work[:5],
            keywords=extract_keywords_from_text(parsed_paper.full_text),
            needs_review=bool(warnings),
            warnings=warnings,
        )

    @staticmethod
    def _collect_section_text(parsed_paper: ParsedPaper) -> dict[str, list[str]]:
        sections: dict[str, list[str]] = {}
        for chunk in parsed_paper.chunks:
            sections.setdefault(chunk.section, []).append(chunk.content)
        return sections

    @staticmethod
    def _join_sections(sections: dict[str, list[str]], keys: list[str]) -> str:
        collected: list[str] = []
        for key in keys:
            collected.extend(sections.get(key, []))
        return "\n\n".join(collected)

    @staticmethod
    def _summarize_section(text: str, fallback: str, limit: int = 400) -> str:
        content = text.strip() or fallback.strip()
        if not content:
            return ""
        snippet = re.split(r"(?<=[.!?])\s+", content)[0]
        return snippet[:limit].strip()

    @staticmethod
    def _infer_method_category(text: str) -> str | None:
        lower_text = text.lower()
        if any(token in lower_text for token in ["transformer", "attention", "bert", "gpt", "llm"]):
            return "transformer_or_llm"
        if any(token in lower_text for token in ["graph", "gnn", "knowledge graph"]):
            return "graph_based"
        if any(token in lower_text for token in ["retrieval", "ranking", "recommendation"]):
            return "retrieval_or_ranking"
        if any(token in lower_text for token in ["contrastive", "self-supervised", "pretrain"]):
            return "representation_learning"
        return None

    @staticmethod
    def _extract_named_items(text: str, keywords: list[str]) -> list[str]:
        candidates: list[str] = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            lower_line = line.lower()
            if any(keyword in lower_line for keyword in keywords):
                matches = re.findall(r"\b[A-Z][A-Za-z0-9\-]{1,}\b", line)
                candidates.extend(matches)
        return normalize_text_list(candidates)[:8]

    @staticmethod
    def _extract_metrics(text: str) -> list[str]:
        common_metrics = [
            "accuracy",
            "precision",
            "recall",
            "f1",
            "auc",
            "ndcg",
            "map",
            "mrr",
            "rmse",
            "mae",
            "bleu",
            "rouge",
            "dice",
            "iou",
        ]
        lower_text = text.lower()
        found = [metric.upper() if len(metric) <= 4 else metric for metric in common_metrics if metric in lower_text]
        return normalize_text_list(found)

    @staticmethod
    def _extract_sentences(text: str, markers: list[str]) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        matched = [sentence.strip() for sentence in sentences if any(marker in sentence.lower() for marker in markers)]
        return normalize_text_list(matched)

    @staticmethod
    def _infer_strengths(text: str, metrics: list[str]) -> list[str]:
        strengths: list[str] = []
        lower_text = text.lower()
        if "efficient" in lower_text or "lightweight" in lower_text:
            strengths.append("方法强调效率或部署友好性。")
        if "robust" in lower_text or "generalization" in lower_text:
            strengths.append("论文强调了模型的鲁棒性或泛化能力。")
        if metrics:
            strengths.append(f"实验报告了 {', '.join(metrics[:3])} 等常见指标。")
        if not strengths:
            strengths.append("论文给出了较完整的方法与实验流程，便于后续横向比较。")
        return strengths[:4]

