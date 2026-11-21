import json
from uuid import uuid4

import pytest
from docx import Document
from pydantic import ValidationError

from formforge.coi_mapper import COIJsonMapper
from formforge.config import Settings
from formforge.field_detector import FieldDetector
from formforge.layout_analyzer import LayoutAnalyzer
from formforge.models import Block, ExtractedDocument, FieldType, Form, Page
from formforge.pipeline import convert
from conftest import SAMPLES


@pytest.mark.parametrize("name", ["zaswiadczenie", "zezwolenie", "zgloszenie", "wielostronicowy"])
@pytest.mark.parametrize("ext", ["pdf", "docx", "xlsx", "ods"])
def test_demo_expected_fields(name, ext):
    data = convert(SAMPLES / f"{name}.{ext}", f"{name}.{ext}", ext, Settings())
    form = Form.model_validate(data["form"])
    expected = json.loads((SAMPLES / "expected_fields.json").read_text())[name]["expected_labels"]
    found = {field.label for field in form.fields}
    assert set(expected) <= found
    assert data["preview_export"]["compatibility"]["official_coi"] is False
    assert data["coi_validation"]["valid"] is True
    assert len(data["stages"]) == 6
    if name == "wielostronicowy":
        assert len(form.pages) == 3


def test_field_types_and_static_text():
    lines = [
        "PESEL *: _____",
        "Kod pocztowy: _____",
        "Data urodzenia: _____",
        "E-mail: _____",
        "Telefon: _____",
        "Kwota: _____",
        "Opis: _____",
        "Adres: _____",
        "Załącznik: _____",
        "Tryb: [ ] Tak [ ] Nie",
        "Wariant (wybierz): Jeden; Dwa",
        "[ ] Akceptuję regulamin",
        "Informacja o przetwarzaniu danych osobowych.",
    ]
    doc = ExtractedDocument(filename="unseen.pdf", format="pdf", pages=[Page(id=1, title="Test")], blocks=[Block(id=f"b{i}", text=line, page=1) for i, line in enumerate(lines)])
    fields = FieldDetector().detect(LayoutAnalyzer().analyze(doc))
    assert {
        FieldType.PESEL,
        FieldType.POSTAL_CODE,
        FieldType.DATE,
        FieldType.EMAIL,
        FieldType.PHONE,
        FieldType.NUMBER,
        FieldType.TEXTAREA,
        FieldType.ADDRESS,
        FieldType.ATTACHMENT,
        FieldType.RADIO,
        FieldType.SELECT,
        FieldType.CHECKBOX,
    } <= {f.field_type for f in fields}
    assert fields[0].required
    assert not any("Informacja" in f.label for f in fields)


def test_layout_order_and_uppercase_field():
    document = ExtractedDocument(
        filename="new.pdf",
        format="pdf",
        pages=[Page(id=1, title="Page")],
        blocks=[Block(id="later", text="PESEL:", page=1, bbox=(10, 50, 80, 60)), Block(id="first", text="I. DANE OSOBOWE", page=1, bbox=(10, 10, 150, 25))],
    )
    result = LayoutAnalyzer().analyze(document)
    assert result.blocks[0].id == "first" and result.blocks[0].kind == "heading"
    assert result.blocks[1].kind == "text"


def test_cycle_rejected(sample_form):
    from formforge.models import ConditionalRule

    first, second = sample_form.fields[:2]
    first.conditions = [ConditionalRule(field_id=second.id, value="x")]
    second.conditions = [ConditionalRule(field_id=first.id, value="y")]
    with pytest.raises(ValidationError):
        Form.model_validate(sample_form.model_dump())


def test_unseen_document_is_content_driven(tmp_path):
    label = "Kod projektu " + uuid4().hex[:8]
    path = tmp_path / "unknown.docx"
    doc = Document()
    doc.add_heading("FORMULARZ NOWEJ SPRAWY", 0)
    doc.add_paragraph(label + ": __________")
    doc.add_paragraph("E-mail: __________")
    doc.save(path)
    data = convert(path, "unknown.docx", "docx", Settings())
    assert label in {f["label"] for f in data["form"]["fields"]}
    assert data["form"]["title"] == "FORMULARZ NOWEJ SPRAWY"


def test_explicit_dependency():
    data = convert(SAMPLES / "wielostronicowy.pdf", "x.pdf", "pdf", Settings())
    form = Form.model_validate(data["form"])
    target = next(f for f in form.fields if f.label == "NIP")
    assert target.conditions and target.conditions[0].value == "Firma"
    parent = next(f for f in form.fields if f.id == target.conditions[0].field_id)
    assert parent.label == "Status"


def test_invalid_references_rejected(sample_form):
    sample_form.fields[0].section = "missing"
    with pytest.raises(ValidationError):
        Form.model_validate(sample_form.model_dump())


def test_official_export_refused(sample_form):
    with pytest.raises(ValueError):
        COIJsonMapper().export(sample_form, official=True)


def test_adapter_has_no_extra_export_keys(sample_form):
    class Adapter:
        def map(self, form):
            return {"actual_schema_key": form.title}

        def validate(self, payload):
            assert set(payload) == {"actual_schema_key"}

    assert set(COIJsonMapper(Adapter()).export(sample_form, official=True)) == {"actual_schema_key"}
