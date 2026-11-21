import shutil
from pathlib import Path

import pytest

from formforge.config import Settings
from formforge.errors import DocumentError
from formforge.extractors import DocumentExtractor
from conftest import SAMPLES


@pytest.mark.parametrize("ext", ["pdf", "docx", "xlsx", "ods"])
def test_real_document_extraction(ext):
    doc = DocumentExtractor(Settings()).extract(SAMPLES / f"zaswiadczenie.{ext}", f"zaswiadczenie.{ext}", ext)
    assert any("PESEL" in b.text for b in doc.blocks)
    assert doc.pages
    if ext == "pdf":
        assert any(b.bbox for b in doc.blocks)
    if ext == "docx":
        assert any(b.kind == "heading" for b in doc.blocks)
    if ext in ("xlsx", "ods"):
        assert all(b.metadata.get("sheet") for b in doc.blocks)


def test_spreadsheet_metadata():
    doc = DocumentExtractor(Settings()).extract(SAMPLES / "zgloszenie.xlsx", "x.xlsx", "xlsx")
    assert any(b.metadata.get("formula") == "=SUM(1,2)" for b in doc.blocks)
    assert any(b.metadata.get("merged_ranges") for b in doc.blocks)
    assert not any(b.text == "3" for b in doc.blocks)


def test_native_pdf_fields(tmp_path):
    from reportlab.pdfgen import canvas

    path = tmp_path / "native.pdf"
    pdf = canvas.Canvas(str(path))
    pdf.drawString(50, 780, "FORMULARZ DANYCH")
    pdf.acroForm.textfield(name="PESEL", tooltip="PESEL", x=50, y=650, width=180, height=25, fieldFlags="required")
    pdf.acroForm.checkbox(name="Zgoda", tooltip="Zgoda", x=50, y=600)
    pdf.save()
    from formforge.pipeline import convert

    data = convert(path, "native.pdf", "pdf", Settings())
    fields = data["form"]["fields"]
    assert any(f["label"] == "PESEL" and f["field_type"] == "pesel" and f["required"] for f in fields)
    assert any(f["label"] == "Zgoda" and f["field_type"] == "checkbox" for f in fields)
    assert all(f["source_reference"]["bbox"] for f in fields)


def test_docx_table_and_multiple_pages():
    doc = DocumentExtractor(Settings()).extract(SAMPLES / "wielostronicowy.docx", "x.docx", "docx")
    assert len(doc.pages) == 3
    assert any(b.method == "docx_table" for b in doc.blocks)


@pytest.mark.ocr
@pytest.mark.parametrize("name", ["zaswiadczenie.png", "zaswiadczenie.jpg", "skan.pdf"])
def test_real_ocr(name):
    if not shutil.which("tesseract"):
        pytest.skip("Local Tesseract is not installed")
    doc = DocumentExtractor(Settings()).extract(SAMPLES / name, name, Path(name).suffix[1:])
    assert any(b.method == "tesseract_ocr" and "PESEL" in b.text.upper() for b in doc.blocks)
    assert any(b.bbox for b in doc.blocks)


@pytest.mark.ocr
def test_geometric_checkbox():
    if not shutil.which("tesseract"):
        pytest.skip("Local Tesseract is not installed")
    doc = DocumentExtractor(Settings()).extract(SAMPLES / "checkbox.png", "checkbox.png", "png")
    assert any(b.method == "ocr_square_candidate" for b in doc.blocks)


def test_pdf_page_limit():
    with pytest.raises(DocumentError) as exc:
        DocumentExtractor(Settings(max_pages=1)).extract(SAMPLES / "wielostronicowy.pdf", "x.pdf", "pdf")
    assert exc.value.code == "page_limit"


def test_corrupted_file(tmp_path):
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"%PDF-1.4\ncorrupt")
    with pytest.raises(DocumentError):
        DocumentExtractor(Settings()).extract(path, "x.pdf", "pdf")


def test_missing_ocr_is_explicit(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(DocumentError) as exc:
        DocumentExtractor(Settings()).extract(SAMPLES / "zaswiadczenie.png", "x.png", "png")
    assert exc.value.code == "ocr_unavailable"
