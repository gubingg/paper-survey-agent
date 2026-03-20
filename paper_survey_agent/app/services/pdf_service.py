from __future__ import annotations

from pathlib import Path

import fitz

from app.schemas.paper_schema import PageBlock, ParsedPage, ParsedPaper
from app.utils.chunk_utils import normalize_academic_text
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PDFService:
    """Service responsible for parsing PDF files into structured text."""

    def parse_pdf(self, file_path: str, paper_id: str) -> ParsedPaper:
        """Parse a PDF and return text, pages, and blocks."""

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        pages: list[ParsedPage] = []
        full_text_parts: list[str] = []

        with fitz.open(path) as document:
            for page_index, page in enumerate(document, start=1):
                text = normalize_academic_text(page.get_text("text", sort=True).strip())
                block_items: list[PageBlock] = []
                for block_number, block in enumerate(page.get_text("blocks")):
                    x0, y0, x1, y1, block_text, *_ = block
                    cleaned = normalize_academic_text((block_text or "").strip())
                    if cleaned:
                        block_items.append(
                            PageBlock(
                                x0=float(x0),
                                y0=float(y0),
                                x1=float(x1),
                                y1=float(y1),
                                text=cleaned,
                                block_no=block_number,
                            )
                        )
                pages.append(ParsedPage(page=page_index, text=text, blocks=block_items))
                if text:
                    full_text_parts.append(text)

        full_text = "\n\n".join(full_text_parts).strip()
        title_guess = self._guess_title(pages, fallback=path.stem)
        parsed_paper = ParsedPaper(
            paper_id=paper_id,
            title_guess=title_guess,
            pages=pages,
            full_text=full_text,
            chunks=[],
        )
        logger.info("Parsed paper %s with %s pages", paper_id, len(pages))
        return parsed_paper

    @staticmethod
    def _guess_title(pages: list[ParsedPage], fallback: str = "") -> str:
        """Guess a paper title from the first page text."""

        if not pages:
            return fallback
        first_lines = [line.strip() for line in pages[0].text.splitlines() if line.strip()]
        candidate_lines = [line for line in first_lines if len(line) > 8]
        return candidate_lines[0][:300] if candidate_lines else fallback
