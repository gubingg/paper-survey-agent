from __future__ import annotations

import os

from app.schemas.paper_schema import PaperChunk
from app.services.embedding_service import EmbeddingService
from app.utils.file_utils import CHROMA_DIR
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    chromadb = None
    Settings = None


class VectorStoreService:
    """Chroma vector index wrapper with local fallback retrieval."""

    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()
        self.enable_chroma = os.getenv("ENABLE_CHROMA", "false").lower() in {"1", "true", "yes", "on"}

    def index_chunks(self, project_id: str, chunks: list[PaperChunk]) -> dict:
        """Index chunks into a persistent Chroma collection when available."""

        if not chunks:
            return {"enabled": False, "indexed": 0, "reason": "No chunks to index."}
        if not self.enable_chroma:
            return {"enabled": False, "indexed": 0, "reason": "Chroma disabled; using local retrieval fallback."}
        if chromadb is None:
            return {"enabled": False, "indexed": 0, "reason": "chromadb is not available."}

        try:
            client = self._build_client()
            collection = client.get_or_create_collection(name=f"project_{project_id}")
            documents = [chunk.content for chunk in chunks]
            embeddings = self.embedding_service.embed_texts(documents)
            metadatas = [
                {
                    "paper_id": chunk.paper_id,
                    "section": chunk.section,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                }
                for chunk in chunks
            ]
            ids = [chunk.chunk_id for chunk in chunks]
            collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
            logger.info("Indexed %s chunks for project %s", len(chunks), project_id)
            return {"enabled": True, "indexed": len(chunks), "reason": "Indexed successfully."}
        except Exception as exc:
            logger.warning("Chroma indexing failed, switching to local retrieval fallback: %s", exc)
            return {"enabled": False, "indexed": 0, "reason": f"Chroma indexing failed: {exc}"}

    def _build_client(self):
        if Settings is not None:
            return chromadb.PersistentClient(path=str(CHROMA_DIR), settings=Settings(anonymized_telemetry=False))
        return chromadb.PersistentClient(path=str(CHROMA_DIR))

    def query_chunks(
        self,
        project_id: str,
        query: str,
        chunks: list[PaperChunk],
        paper_id: str | None = None,
        top_k: int = 5,
    ):
        """Query internal chunk evidence, preferring Chroma and falling back to lexical scoring."""

        from app.schemas.agent_schema import EvidenceSnippet
        import math
        import re
        from collections import Counter

        filtered_chunks = [chunk for chunk in chunks if paper_id is None or chunk.paper_id == paper_id]
        if not filtered_chunks:
            return []

        if self.enable_chroma and chromadb is not None:
            try:
                client = self._build_client()
                collection = client.get_collection(name=f"project_{project_id}")
                query_embedding = self.embedding_service.embed_texts([query])[0]
                where = {"paper_id": paper_id} if paper_id else None
                result = collection.query(query_embeddings=[query_embedding], n_results=top_k, where=where)
                evidence_items: list[EvidenceSnippet] = []
                ids = result.get("ids", [[]])[0]
                docs = result.get("documents", [[]])[0]
                metadatas = result.get("metadatas", [[]])[0]
                distances = result.get("distances", [[]])[0] if result.get("distances") else [0.0] * len(ids)
                for index, chunk_id in enumerate(ids):
                    metadata = metadatas[index] or {}
                    score = max(0.0, 1.0 - float(distances[index] or 0.0)) if index < len(distances) else 0.0
                    evidence_items.append(
                        EvidenceSnippet(
                            paper_id=metadata.get("paper_id", paper_id or ""),
                            chunk_id=chunk_id,
                            section=metadata.get("section", "unknown"),
                            page_start=int(metadata.get("page_start", 0)),
                            page_end=int(metadata.get("page_end", 0)),
                            content=docs[index],
                            score=score,
                        )
                    )
                return evidence_items
            except Exception as exc:
                logger.warning("Chroma retrieval failed, falling back to lexical search: %s", exc)

        query_terms = [token for token in re.findall(r"[A-Za-z\u4e00-\u9fff0-9\-]+", query.lower()) if len(token) > 1]
        if not query_terms:
            query_terms = [query.lower()]
        scored: list[tuple[float, PaperChunk]] = []
        for chunk in filtered_chunks:
            content_lower = chunk.content.lower()
            matches = Counter(term for term in query_terms if term in content_lower)
            if not matches:
                continue
            density = sum(matches.values()) / max(len(query_terms), 1)
            score = min(0.99, density / max(math.log(len(chunk.content) + 10), 1.0))
            scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            EvidenceSnippet(
                paper_id=chunk.paper_id,
                chunk_id=chunk.chunk_id,
                section=chunk.section,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                content=chunk.content,
                score=score,
            )
            for score, chunk in scored[:top_k]
        ]
