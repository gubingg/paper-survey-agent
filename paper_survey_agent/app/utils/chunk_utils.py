from __future__ import annotations

import re
import uuid
from collections import Counter

from app.schemas.paper_schema import PaperChunk, ParsedPage


SECTION_HINTS = {
    "abstract": ["abstract"],
    "introduction": ["introduction", "background"],
    "method": ["method", "approach", "architecture", "model"],
    "experiments": ["experiment", "evaluation", "results"],
    "conclusion": ["conclusion", "future work", "discussion"],
}


def normalize_academic_text(text: str) -> str:
    """Clean PDF extraction artifacts while keeping paragraph structure."""

    if not text:
        return ""

    text = text.replace("\u00ad", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?<=[A-Za-z])\-\s*\n\s*(?=[A-Za-z])", "", text)

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    normalized_paragraphs: list[str] = []
    for paragraph in paragraphs:
        paragraph = re.sub(r"\s*\n\s*", " ", paragraph)
        paragraph = re.sub(r"(?<=[A-Za-z])\-\s+(?=[a-z])", "", paragraph)
        paragraph = re.sub(r"\s+([,.;:!?%)\]])", r"\1", paragraph)
        paragraph = re.sub(r"([([\]])\s+", r"\1", paragraph)
        paragraph = re.sub(r"\s+", " ", paragraph).strip()
        if paragraph:
            normalized_paragraphs.append(paragraph)
    return "\n\n".join(normalized_paragraphs)


def infer_section(content: str) -> str:
    """Infer a coarse paper section from chunk content."""

    lower_content = content.lower()
    for section, keywords in SECTION_HINTS.items():
        if any(keyword in lower_content[:500] for keyword in keywords):
            return section
    return "unknown"


def extract_year(text: str) -> int | None:
    """Extract a likely publication year from text."""

    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", text[:2000])
    if not year_match:
        return None
    year = int(year_match.group(1))
    if 1990 <= year <= 2100:
        return year
    return None


def normalize_text_list(items: list[str]) -> list[str]:
    """Normalize a string list while preserving order."""

    seen: set[str] = set()
    normalized: list[str] = []
    for item in items:
        cleaned = normalize_academic_text(item)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;:-")
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            normalized.append(cleaned)
    return normalized


def extract_keywords_from_text(text: str, limit: int = 8) -> list[str]:
    """Build lightweight keywords without external NLP libraries."""

    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", text.lower())
    stopwords = {
        "this",
        "that",
        "with",
        "from",
        "using",
        "paper",
        "method",
        "results",
        "based",
        "their",
        "have",
        "show",
        "into",
        "than",
        "also",
        "such",
        "these",
        "been",
    }
    counts = Counter(token for token in tokens if token not in stopwords)
    return [token for token, _ in counts.most_common(limit)]


def build_chunks(
    paper_id: str,
    pages: list[ParsedPage],
    max_chars: int = 5000,
    overlap_chars: int = 800,
) -> list[PaperChunk]:
    """Chunk parsed pages by paragraph while keeping page metadata."""

    paragraph_units: list[tuple[int, str]] = []
    for page in pages:
        paragraphs = [item.strip() for item in re.split(r"\n\s*\n", page.text) if item.strip()]
        if not paragraphs and page.text.strip():
            paragraphs = [page.text.strip()]
        for paragraph in paragraphs:
            paragraph_units.append((page.page, paragraph))

    if not paragraph_units:
        return []

    chunks: list[PaperChunk] = []
    current_parts: list[str] = []
    current_pages: list[int] = []

    def flush_chunk(parts: list[str], pages_used: list[int]) -> None:
        if not parts:
            return
        content = "\n\n".join(parts).strip()
        if not content:
            return
        chunks.append(
            PaperChunk(
                chunk_id=f"chunk_{uuid.uuid4().hex[:10]}",
                paper_id=paper_id,
                section=infer_section(content),
                page_start=min(pages_used),
                page_end=max(pages_used),
                content=content,
            )
        )

    for page_no, paragraph in paragraph_units:
        projected = "\n\n".join(current_parts + [paragraph])
        if current_parts and len(projected) > max_chars:
            overlap_parts: list[str] = []
            overlap_count = 0
            for item in reversed(current_parts):
                overlap_parts.insert(0, item)
                overlap_count += len(item)
                if overlap_count >= overlap_chars:
                    break
            flush_chunk(current_parts, current_pages)
            current_parts = overlap_parts + [paragraph]
            current_pages = [page_no]
        else:
            current_parts.append(paragraph)
            current_pages.append(page_no)

    flush_chunk(current_parts, current_pages)
    return chunks
