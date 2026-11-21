"""Regression evidence for real V03 failures; no expected JSON lookups in runtime."""

from pathlib import Path

import pytest
from docx import Document
from openpyxl import Workbook
from PIL import Image

from formforge.config import Settings
from formforge.errors import DocumentError
from formforge.extractors import DocumentExtractor
from formforge.file_validator import FileValidator
from formforge.models import Block, ExtractedDocument, Page
from formforge.layout_analyzer import LayoutAnalyzer
from formforge.document_understanding import understand
from formforge.field_detector import FieldDetector
from formforge.pipeline import convert

ROOT = Path(__file__).resolve().parents[1]


def source(group, ext):
    directory = ROOT / "reference/coi-official/forms" / group
    if not directory.is_dir():
        pytest.skip("Organizer source pack is separately supplied; included in the full review ZIP")
    return next(p for p in directory.iterdir() if p.suffix.lower() == "." + ext and "wizualizac" not in p.name)


@pytest.mark.parametrize("group,pages", [("02", 2), ("08", 6)])
def test_drawing_textboxes_preserve_text_and_pages_without_fallback_duplicate(group, pages):
    d = DocumentExtractor(Settings()).extract(source(group, "docx"), "unseen.docx", "docx")
    assert len(d.pages) == pages
    boxes = [b for b in d.blocks if b.method == "docx_textbox"]
    assert len(boxes) > 40 and any(b.bbox for b in boxes)
    assert len({(b.page, b.text, b.bbox) for b in boxes}) == len(boxes)


def test_recursive_docx_tables(tmp_path):
    d = Document()
    outer = d.add_table(rows=1, cols=2)
    outer.cell(0, 0).text = "Dane"
    nested = outer.cell(0, 1).add_table(rows=1, cols=2)
    nested.cell(0, 0).text = "Numer zgłoszenia:"
    path = tmp_path / "nested.docx"
    d.save(path)
    extracted = DocumentExtractor(Settings()).extract(path, path.name, "docx")
    b = next(b for b in extracted.blocks if "Numer zgłoszenia" in b.text)
    assert b.metadata["nested_depth"] == 1 and b.metadata["paired_blank"]


def test_sparse_styled_xlsx_and_merged_cells(tmp_path):
    book = Workbook()
    sheet = book.active
    sheet.merge_cells("A1:C1")
    sheet["A1"] = "Numer sprawy:"
    sheet["D1"] = ""
    sheet["ZZ10000"].number_format = "0"
    path = tmp_path / "sparse.xlsx"
    book.save(path)
    d = DocumentExtractor(Settings()).extract(path, path.name, "xlsx")
    field = next(b for b in d.blocks if b.text == "Numer sprawy:")
    assert field.metadata["column_span"] == 3
    assert field.metadata["paired_blank"]
    assert len(d.blocks) == 1


def test_real_large_sheet_does_not_count_formatting_rectangle():
    d = DocumentExtractor(Settings()).extract(source("08", "xlsx"), "unknown.xlsx", "xlsx")
    assert len(d.blocks) > 50


def test_large_image_tiles_cover_source_without_omission(tmp_path, monkeypatch):
    path = tmp_path / "strip.png"
    Image.new("RGB", (500, 2600), "white").save(path)
    seen = []
    monkeypatch.setattr(DocumentExtractor, "ocr", lambda self, img, page_id, **kw: (seen.append(img.size), self.add("Numer: _____", page_id, method="test")))
    d = DocumentExtractor(Settings(max_image_pixels=100000, max_source_image_pixels=2000000)).extract(path, path.name, "png")
    tiles = d.analysis["image_tiles"]
    assert tiles[0]["source_bbox"][1] == 0 and tiles[-1]["source_bbox"][3] == 2600
    assert all(a["source_bbox"][3] == b["source_bbox"][1] for a, b in zip(tiles, tiles[1:]))
    assert all(w * h <= 100000 for w, h in seen)


def test_source_pixel_budget_has_precise_error(tmp_path):
    path = tmp_path / "huge.png"
    Image.new("RGB", (500, 500)).save(path)
    with pytest.raises(DocumentError) as e:
        DocumentExtractor(Settings(max_source_image_pixels=100000)).extract(path, path.name, "png")
    assert e.value.status == 413 and e.value.code == "pixel_limit"


def test_partial_tile_failure_retains_other_pages(tmp_path, monkeypatch):
    path = tmp_path / "partial.png"
    Image.new("RGB", (400, 600), "white").save(path)

    def ocr(self, image, page, **kwargs):
        if page == 1:
            raise DocumentError("timeout", 408, "ocr_timeout")
        self.add("PESEL: _____", page, method="test")

    monkeypatch.setattr(DocumentExtractor, "ocr", ocr)
    d = DocumentExtractor(Settings(max_image_pixels=100000)).extract(path, path.name, "png")
    assert d.blocks and any("Częściowy" in w for w in d.warnings)


def test_jpe_and_docx_under_doc_extension_are_verified():
    assert FileValidator(Settings()).validate("unseen.JPE", "image/jpeg", source("07", "jpe").read_bytes()) == "jpe"
    assert FileValidator(Settings()).validate("unseen.DOC", "application/msword", source("05", "doc").read_bytes()) == "docx"
    # 0.4 intentionally adds verified read-only Word97 binary text support.
    assert FileValidator(Settings()).validate("binary.doc", "application/msword", source("01", "doc").read_bytes()) == "doc"


def test_real_certificate_checkboxes_and_other_dependency():
    d = convert(source("03", "pdf"), "unknown.pdf", "pdf", Settings())
    fields = d["form"]["fields"]
    choices = [f for f in fields if f["field_type"] == "checkbox"]
    assert len(choices) == 5
    detail = next(f for f in fields if "doprecyzowanie" in f["label"])
    assert detail["conditions"][0]["value"] is True
    assert detail["conditions"][0]["evidence"] and detail["conditions"][0]["requires_review"]
    assert all(f["decision_reasons"] for f in fields)
    assert d["coi_validation"]["valid"]


def test_real_road_triplet_numbers_survive():
    result = convert(source("06", "pdf"), "unknown.pdf", "pdf", Settings())
    for label in ["długość", "szerokość", "razem"]:
        fields = [f for f in result["form"]["fields"] if f["label"] == label]
        assert len(fields) == 8 and all(f["field_type"] == "number" for f in fields)
    assert result["normalization"]["standard_additions"] == 0
    assert result["coi_validation"]["valid"]


def test_paper_signature_and_legal_prose_are_not_inputs():
    doc = ExtractedDocument(
        filename="unseen.pdf",
        format="pdf",
        pages=[Page(id=1, title="Test")],
        blocks=[
            Block(id="b1", page=1, text="PESEL: _____"),
            Block(id="b2", page=1, text="Podpis wnioskodawcy: _____"),
            Block(id="b3", page=1, text="1. Wypełnij wielkimi literami: _____"),
            Block(id="b4", page=1, text="Klauzula informacyjna"),
            Block(id="b5", page=1, text="Kontakt administratora: _____"),
        ],
    )
    fields = FieldDetector().detect(understand(LayoutAnalyzer().analyze(doc)))
    assert [f.label for f in fields] == ["PESEL"]


def test_dictionary_catalog_is_searchable_without_invented_values(client):
    data = client.get("/api/v1/dictionaries?q=Kraj").json()
    assert data["items"][0]["id"] == "Kraje" and data["items"][0]["values"] == []
    assert not data["values_available"]


def test_natural_source_condition_is_evidenced_and_reviewed():
    from formforge.models import Form, Section, SourceReference, FormField
    from formforge.conditions import ConditionalRulesBuilder

    section = Section(id="s", title="Dane", page=1, order=0)
    base = dict(page=1, section="s", confidence=0.9, detection_method="test", source_reference=SourceReference(page=1, block_id="b", text="source"))
    parent = FormField(id="f_mode", label="Sposób zwrotu", field_type="radio", options=["Gotówka", "Przelew"], order=0, **base)
    target = FormField(id="f_account", label="Numer rachunku", field_type="text", order=1, **base)
    doc = ExtractedDocument(
        filename="unseen.pdf", format="pdf", pages=[Page(id=1, title="Dane")], blocks=[Block(id="b", page=1, text="Jeśli wybierzesz „Przelew”, wpisz „Numer rachunku”")]
    )
    assert ConditionalRulesBuilder().apply(doc, [parent, target], [section]) == {"b"}
    assert target.conditions[0].evidence == doc.blocks[0].text and target.conditions[0].requires_review
    Form(id="test", title="Formularz", pages=doc.pages, sections=[section], fields=[parent, target])


def test_separate_pdf_objects_form_one_sex_radio_group():
    result = convert(source("07", "pdf"), "unknown.pdf", "pdf", Settings())
    fields = [f for f in result["form"]["fields"] if f["label"].strip(" :") == "Płeć"]
    assert len(fields) == 1 and fields[0]["field_type"] == "radio"
    assert fields[0]["options"] == ["pies", "suka"]
    assert any(g["repeat_key"] == "source_repeated_block" for g in result["form"]["groups"])
    assert any(q["field"]["type"] == "REPEATING_SECTION" for tab in result["export"]["tabs"] for q in tab["questions"])


def test_textbox_forms_recover_answer_shapes_not_only_words():
    result = convert(source("02", "docx"), "unknown.docx", "docx", Settings())
    assert len(result["form"]["fields"]) >= 20
    assert any(f["field_type"] == "nip" for f in result["form"]["fields"])


def test_ocr_word_geometry_separates_distant_columns():
    from formforge.ocr import read_lines, Variant

    data = {
        "text": ["Adres", "Urząd"],
        "left": [10, 400],
        "top": [20, 20],
        "width": [50, 50],
        "height": [14, 14],
        "conf": [95, 95],
        "block_num": [1, 1],
        "par_num": [1, 1],
        "line_num": [1, 1],
    }
    lines = read_lines(data, Variant("test", Image.new("L", (600, 100), 255)))
    assert [line["text"] for line in lines] == ["Adres", "Urząd"]


def test_unreadable_ocr_and_numeric_noise_remain_diagnostics():
    doc = ExtractedDocument(
        filename="unseen.png",
        format="png",
        pages=[Page(id=1, title="Scan")],
        blocks=[
            Block(id="b1", page=1, text="ee ee ey", method="tesseract_ocr", confidence=0.15, metadata={"label_input_pair": True}),
            Block(id="b2", page=1, text="Kwota: ____ 11111112 ____"),
        ],
    )
    parsed = understand(LayoutAnalyzer().analyze(doc))
    fields = FieldDetector().detect(parsed)
    assert [f.label for f in fields] == ["Kwota"]
    assert parsed.blocks[0].text == "ee ee ey" and parsed.blocks[0].kind == "information"
