from __future__ import annotations

import pytest

fitz = pytest.importorskip("fitz")

from app.services.pdf_service import PDFService


def test_parse_pdf(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Sample Paper Title\nAbstract\nThis paper studies recommendation systems.")
    document.save(pdf_path)
    document.close()

    service = PDFService()
    parsed = service.parse_pdf(str(pdf_path), "paper_test")

    assert parsed.paper_id == "paper_test"
    assert parsed.title_guess.startswith("Sample Paper Title")
    assert "recommendation systems" in parsed.full_text.lower()
    assert len(parsed.pages) == 1
    assert parsed.chunks == []
