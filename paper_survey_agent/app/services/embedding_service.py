from __future__ import annotations

import hashlib
import os
from itertools import islice

import requests

from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Embedding wrapper with API batching and offline fallback."""

    def __init__(self) -> None:
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.model_name = os.getenv("TEXT_EMBEDDING_MODEL_NAME", "text-embedding-v4")
        self.base_url = os.getenv(
            "TEXT_EMBEDDING_BASE_URL",
            "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding",
        )
        self.timeout = int(os.getenv("TEXT_EMBEDDING_TIMEOUT", "90"))
        self.batch_size = int(os.getenv("TEXT_EMBEDDING_BATCH_SIZE", "8"))

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed texts via DashScope when available, otherwise return deterministic pseudo-vectors."""

        normalized_texts = [self._normalize_text(text) for text in texts]
        if self.api_key:
            try:
                return self._embed_with_api(normalized_texts)
            except Exception as exc:
                logger.warning("Embedding API failed, falling back to local vectors: %s", exc)
        return [self._hash_embedding(text) for text in normalized_texts]

    def _embed_with_api(self, texts: list[str]) -> list[list[float]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        embeddings: list[list[float]] = []
        iterator = iter(texts)
        while True:
            batch = list(islice(iterator, self.batch_size))
            if not batch:
                break
            payload = {
                "model": self.model_name,
                "input": {"texts": batch},
                "parameters": {"text_type": "document"},
            }
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            outputs = response.json().get("output", {}).get("embeddings", [])
            if len(outputs) != len(batch):
                raise ValueError(f"Embedding output size mismatch: expected {len(batch)}, got {len(outputs)}")
            embeddings.extend(item.get("embedding", []) for item in outputs)
        return embeddings

    @staticmethod
    def _normalize_text(text: str, max_chars: int = 3000) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            return "empty"
        return cleaned[:max_chars]

    @staticmethod
    def _hash_embedding(text: str, dimensions: int = 16) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [digest[index] / 255 for index in range(dimensions)]
        return values
