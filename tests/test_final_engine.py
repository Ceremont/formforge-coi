"""Final regression gates for actual defects; source fixtures are optional."""

import io
from pathlib import Path
import struct

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import olefile
import pytest

from formforge.config import Settings
from formforge.errors import DocumentError
from formforge.extractors import DocumentExtractor
from formforge.file_validator import FileValidator
from formforge.form_validator import FormValidator
from formforge.models import ConditionalRule, FieldType, Block, ExtractedDocument, Page
from formforge.legacy_doc import display_text, inspect_doc, parse_piece_table
from formforge.pipeline import convert
from scripts.doc_sample import document_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_binary_doc_roundtrip_polish_fields_and_codes(tmp_path):
    data = document_bytes("WNIOSEK O WYDANIE ZEZWOLENIA\rPESEL: ____\rImię i nazwisko: ____\r\x13 HYPERLINK secret \x14Widoczny tekst\x15\r")
    assert FileValidator(Settings()).validate("nieznany.doc", "application/msword", data) == "doc"
    path = tmp_path / "nieznany.doc"
    path.write_bytes(data)
    result = convert(path, path.name, "doc", Settings())
    assert {f["field_type"] for f in result["detected_form"]["fields"]} >= {"pesel", "text"}
    assert result["coi_validation"]["valid"] and result["quality"]["status"] == "partial"
    texts = " ".join(b["text"] for b in result["document"]["blocks"])
    assert "Widoczny tekst" in texts and "secret" not in texts


def test_doc_rejects_encryption_and_vba():
    data = bytearray(document_bytes("PESEL: ____\r"))
    struct.pack_into("<H", data, 1024 + 10, 0x1300)
    with pytest.raises(DocumentError) as e:
        inspect_doc(bytes(data))
    assert e.value.code == "encrypted_doc"
    data = bytearray(document_bytes("PESEL: ____\r"))
    offset = 512 + 2 * 128
    data[offset : offset + 64] = bytes(64)
    data[offset : offset + 8] = "VBA\x00".encode("utf-16le")
    struct.pack_into("<H", data, offset + 64, 8)
    with pytest.raises(DocumentError) as e:
        inspect_doc(bytes(data))
    assert e.value.code == "macros_rejected"


def test_doc_rejects_broken_piece_table_and_large_counts():
    data = document_bytes("Tekst\r")
    with olefile.OleFileIO(io.BytesIO(data)) as ole:
        word = bytearray(ole.openstream("WordDocument").read())
        table = bytearray(ole.openstream("1Table").read())
    struct.pack_into("<I", table, 9, 0)
    with pytest.raises(DocumentError):
        parse_piece_table(word, table)
    struct.pack_into("<I", word, 76, 2_000_001)
    with pytest.raises(DocumentError) as e:
        parse_piece_table(word, table)
    assert e.value.status == 413


def test_field_instruction_nesting_is_not_executed():
    assert display_text("A\x13code\x13nested\x14result\x15\x14shown\x15B") == "AshownB"


def test_pdf_zero_area_source_space_is_preserved():
    from formforge.pdf_text import lines

    class Text:
        def count_chars(self):
            return 5

        def get_text_range(self, i, n):
            return "AB CD"[i : i + n]

        def get_charbox(self, i, **kwargs):
            return (i * 4, 0, i * 4 + (0 if i == 2 else 4), 0 if i == 2 else 10)

    assert next(lines(Text(), 100))[0] == "AB CD"


def test_docx_blank_tab_leader_has_source_backed_textarea(tmp_path):
    document = Document()
    document.add_heading("Wniosek o informację", 0)
    document.add_heading("Przedmiot wniosku", 1)
    document.add_paragraph("Wnoszę o udostępnienie informacji:")
    paragraph = document.add_paragraph("\t")
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:leader"), "dot")
    tab.set(qn("w:val"), "right")
    tab.set(qn("w:pos"), "8000")
    tabs.append(tab)
    paragraph._p.get_or_add_pPr().append(tabs)
    path = tmp_path / "tab.docx"
    document.save(path)
    result = DocumentExtractor(Settings()).extract(path, path.name, "docx")
    field = next(b for b in result.blocks if b.method == "docx_tab_leader")
    assert field.text == "Przedmiot wniosku" and field.metadata["native_type"] == "textarea"


def test_conflicting_conditions_are_errors(sample_form):
    parent, target = sample_form.fields[:2]
    target.conditions = [ConditionalRule(field_id=parent.id, value="Tak"), ConditionalRule(field_id=parent.id, value="Nie")]
    assert any(i.code == "conflicting_conditions" and i.severity == "error" for i in FormValidator().inspect(sample_form))


def test_quality_review_refreshes_after_edit(client, sample_form):
    first = client.post("/api/v1/forms/validate", json={"form": sample_form.model_dump(mode="json")}).json()
    sample_form.fields[0].field_type = FieldType.SELECT
    sample_form.fields[0].options = []
    second = client.post("/api/v1/forms/validate", json={"form": sample_form.model_dump(mode="json")}).json()
    assert second["quality_review"]["counts"]["error"] > first["quality_review"]["counts"]["error"]
    assert any(i["code"] == "missing_options" and i["recommendation"] for i in second["quality_review"]["diagnostics"])
    assert not second["quality_review"]["checks"]["actual_import_verified"]


def test_docx_blank_table_rows_keep_individual_static_cells(tmp_path):
    document = Document()
    document.add_heading("Zgłoszenie produktów", 0)
    table = document.add_table(rows=4, cols=3)
    for cell, title in zip(table.rows[0].cells, ["Produkt", "Liczba", "Uwagi"]):
        cell.text = title
    path = tmp_path / "table.docx"
    document.save(path)
    result = convert(path, path.name, "docx", Settings())
    fields = result["detected_form"]["fields"]
    assert len(fields) == 9
    assert sum(f["field_type"] == "number" for f in fields) == 3
    assert len({f["source_reference"]["cell"] for f in fields}) == 9
    assert all(g["repeat_key"] is None for g in result["form"]["groups"])
    assert result["coi_validation"]["valid"]


def test_same_line_caption_after_answer_marker_is_a_source_label(tmp_path):
    document = Document()
    document.add_heading("Wniosek", 0)
    document.add_paragraph("…………………… (imię i nazwisko)")
    document.add_paragraph("…………………… (numer telefonu)")
    path = tmp_path / "caption.docx"
    document.save(path)
    result = convert(path, path.name, "docx", Settings())
    assert {f["field_type"] for f in result["detected_form"]["fields"]} == {"text", "phone"}


def test_numbered_captions_and_footnotes_remain_fields():
    from formforge.layout_analyzer import LayoutAnalyzer
    from formforge.document_understanding import understand
    from formforge.field_detector import FieldDetector

    document = ExtractedDocument(
        filename="unknown.pdf",
        format="pdf",
        pages=[Page(id=1, title="Test", width=400, height=300)],
        blocks=[
            Block(id="a", page=1, text="3. Nazwisko", bbox=(10, 10, 80, 22)),
            Block(id="b", page=1, text="___", kind="blank", bbox=(10, 25, 200, 50)),
            Block(id="c", page=1, text="4. Numer PESEL3", bbox=(10, 70, 110, 82)),
            Block(id="d", page=1, text="___", kind="blank", bbox=(10, 85, 200, 110)),
        ],
    )
    analyzed = understand(LayoutAnalyzer().analyze(document))
    fields = FieldDetector().detect(analyzed)
    assert [(f.label, f.field_type) for f in fields] == [("Nazwisko", FieldType.TEXT), ("Numer PESEL3", FieldType.PESEL)]
    assert fields[1].requires_review


def test_unsupported_boolean_option_keeps_data_and_reports_gap(sample_form):
    from formforge.coi_mapper import export_bundle

    parent, target = sample_form.fields[:2]
    parent.field_type = FieldType.SELECT
    parent.options = []
    parent.coi.dictionary_name = "Kraje"
    target.conditions = [ConditionalRule(field_id=parent.id, value=True, requires_review=True)]
    payload, report = export_bundle(sample_form)
    assert report["valid"] and payload["tabs"]
    assert any(i["code"] == "boolean_condition_unsupported" and i["field_id"] == parent.id for i in report["unsupported_features"])
    assert target.conditions[0].value is True
