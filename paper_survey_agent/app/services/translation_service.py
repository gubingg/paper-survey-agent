from __future__ import annotations

import json
import os
import re
import time

import requests

from app.schemas.paper_schema import PaperSchema
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TranslationService:
    """Translate extracted narrative fields into Chinese when the user requests it."""

    _cooldown_until = 0.0

    def __init__(self) -> None:
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.model_name = os.getenv("QWEN_MODEL_NAME", "qwen3-max")
        self.base_url = os.getenv(
            "QWEN_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        )
        self.timeout = int(os.getenv("QWEN_TRANSLATE_TIMEOUT", "45"))
        self.max_retries = int(os.getenv("QWEN_TRANSLATE_RETRIES", "1"))
        self.cooldown_seconds = int(os.getenv("QWEN_TRANSLATE_COOLDOWN", "600"))
        self.enable_translation = os.getenv("ENABLE_ONLINE_TRANSLATION", "true").lower() in {"1", "true", "yes", "on"}

    def localize_schema(self, schema: PaperSchema) -> PaperSchema:
        """Translate schema fields to Chinese when they are primarily English."""

        if not self._translation_available():
            return schema

        payload = self._build_translation_payload(schema)
        if not any(value for value in payload.values()):
            return schema

        for attempt in range(1, self.max_retries + 1):
            try:
                translated = self._translate_payload(payload)
                self._apply_translation(schema, translated)
                return schema
            except Exception as exc:
                logger.warning(
                    "Schema translation attempt %s/%s failed for %s: %s",
                    attempt,
                    self.max_retries,
                    schema.paper_id,
                    exc,
                )
                if attempt < self.max_retries:
                    time.sleep(0.5 * attempt)
        self._enter_cooldown()
        return schema

    def localize_schemas(self, schemas: list[PaperSchema]) -> list[PaperSchema]:
        """Translate a list of schemas in place and return them."""

        return [self.localize_schema(schema) for schema in schemas]

    def localize_text(self, text: str, field_name: str = "text") -> str:
        """Translate one free-text field into Chinese when it is mostly English."""

        if not self._translation_available() or not text or not self._looks_english(text):
            return text

        payload = {field_name: text}
        for attempt in range(1, self.max_retries + 1):
            try:
                translated = self._translate_payload(payload)
                value = translated.get(field_name)
                return value.strip() if isinstance(value, str) and value.strip() else text
            except Exception as exc:
                logger.warning("Text translation attempt %s/%s failed: %s", attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    time.sleep(0.5 * attempt)
        self._enter_cooldown()
        return text

    def _translation_available(self) -> bool:
        return self.enable_translation and bool(self.api_key) and time.time() >= self.__class__._cooldown_until

    def _enter_cooldown(self) -> None:
        self.__class__._cooldown_until = time.time() + self.cooldown_seconds

    def _translate_payload(self, payload: dict) -> dict:
        prompt = (
            "请把下面 JSON 中适合展示给中文用户的叙述性字段翻译成中文。"
            "数据集名称、模型缩写、指标缩写、论文简称尽量保留原文。"
            "输出必须仍然是合法 JSON，键名保持不变，不要添加解释。\n\n"
            f"输入 JSON:\n{json.dumps(payload, ensure_ascii=False)}"
        )
        request_payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "你是学术文本翻译助手，只返回 JSON。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(self.base_url, headers=headers, json=request_payload, timeout=self.timeout)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)

    @staticmethod
    def _looks_english(text: str) -> bool:
        letters = re.findall(r"[A-Za-z]", text)
        cjk = re.findall(r"[\u4e00-\u9fff]", text)
        return bool(letters) and len(letters) >= len(cjk)

    def _build_translation_payload(self, schema: PaperSchema) -> dict:
        return {
            "title": schema.title if self._looks_english(schema.title) else "",
            "research_problem": schema.research_problem if self._looks_english(schema.research_problem) else "",
            "method": schema.method if self._looks_english(schema.method) else "",
            "main_results": schema.main_results if self._looks_english(schema.main_results) else "",
            "strengths": schema.strengths if any(self._looks_english(item) for item in schema.strengths) else [],
            "limitations": schema.limitations if any(self._looks_english(item) for item in schema.limitations) else [],
            "future_work": schema.future_work if any(self._looks_english(item) for item in schema.future_work) else [],
        }

    @staticmethod
    def _apply_translation(schema: PaperSchema, translated: dict) -> None:
        for field_name in ["title", "research_problem", "method", "main_results"]:
            value = translated.get(field_name)
            if isinstance(value, str) and value.strip():
                setattr(schema, field_name, value.strip())

        for field_name in ["strengths", "limitations", "future_work"]:
            value = translated.get(field_name)
            if isinstance(value, list) and value:
                setattr(schema, field_name, [str(item).strip() for item in value if str(item).strip()])

