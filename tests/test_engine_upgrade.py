import json
from pathlib import Path
from formforge.models import FieldType

import pytest
from pydantic import ValidationError

from formforge.config import Settings
from formforge.dictionaries import DictionaryMatcher, DictionaryRegistry
from formforge.field_detector import FieldDetector
from formforge.form_validator import FormValidator, valid_identifier
from formforge.layout_analyzer import LayoutAnalyzer
from formforge.local_ai import assist, train
from formforge.models import Block, ConditionalRule, DictionaryReference, ExtractedDocument, Form, Page, FieldGroup
from formforge.pipeline import convert


def document(blocks):
    return ExtractedDocument(filename="development.pdf", format="pdf", pages=[Page(id=1, title="Development", width=600, height=800)], blocks=blocks)


def test_above_and_left_geometry():
    source = document(
        [
            Block(id="a", text="Imię", page=1, bbox=(40, 40, 90, 52)),
            Block(id="input1", text="___", kind="blank", page=1, bbox=(40, 65, 210, 67)),
            Block(id="b", text="NIP", page=1, bbox=(300, 40, 340, 52)),
            Block(id="input2", text="___", kind="blank", page=1, bbox=(355, 40, 520, 60)),
        ]
    )
    analyzed = LayoutAnalyzer().analyze(source)
    fields = FieldDetector().detect(analyzed)
    assert {f.label for f in fields} == {"Imię", "NIP"}
    assert all(f.source_reference.input_bbox for f in fields)
    assert next(f for f in fields if f.label == "NIP").field_type == "nip"


def test_repeated_labels_are_not_deduplicated():
    source = document([Block(id="one", text="Imię: ___", page=1, bbox=(30, 50, 160, 60)), Block(id="two", text="Imię: ___", page=1, bbox=(30, 150, 160, 160))])
    assert len(FieldDetector().detect(LayoutAnalyzer().analyze(source))) == 2


def test_column_reading_order_and_legal_text():
    source = document(
        [
            Block(id="a", text="Imię: ___", page=1, bbox=(40, 40, 150, 50)),
            Block(id="b", text="Telefon: ___", page=1, bbox=(330, 40, 470, 50)),
            Block(id="c", text="Nazwisko: ___", page=1, bbox=(40, 90, 150, 100)),
            Block(id="d", text="E-mail: ___", page=1, bbox=(330, 90, 470, 100)),
        ]
    )
    result = LayoutAnalyzer().analyze(source)
    assert [b.id for b in result.blocks] == ["a", "c", "b", "d"]
    legal = document([Block(id="l", text="Podstawa prawna: art. 10 ustawy.", page=1)])
    assert not FieldDetector().detect(LayoutAnalyzer().analyze(legal))


def test_real_pdf_vector_input(tmp_path):
    from reportlab.pdfgen import canvas

    path = tmp_path / "vector.pdf"
    pdf = canvas.Canvas(str(path))
    pdf.drawString(45, 780, "DANE OSOBY")
    pdf.drawString(45, 720, "REGON")
    pdf.line(45, 700, 230, 700)
    pdf.save()
    data = convert(path, path.name, "pdf", Settings())
    assert any(f["label"] == "REGON" and f["source_reference"]["input_bbox"] for f in data["form"]["fields"])


@pytest.mark.parametrize(
    "value,kind,valid", [("8567346215", "nip", True), ("8567346216", "nip", False), ("192598184", "regon", True), ("000000000", "regon", False), ("abcdefghij", "nip", False)]
)
def test_nip_regon_checksums(value, kind, valid):
    assert valid_identifier(value, kind) == valid


def test_dictionary_registry_and_proposal(sample_form, tmp_path):
    field = sample_form.fields[0]
    field.label = "Wariant"
    field.options = ["A", "B"]
    entry = DictionaryReference(id="local_variants", title="Wariant", source="proposed", values=["A", "B"])
    used = DictionaryMatcher().bind([field], DictionaryRegistry([entry]))
    assert field.dictionary.id == "local_variants" and used[0].source == "proposed"
    proposals = DictionaryMatcher().bind([field], DictionaryRegistry())
    assert proposals[0].id.startswith("proposed_")
    path = tmp_path / "registry.json"
    path.write_text(json.dumps([entry.model_dump()]))
    assert DictionaryRegistry.from_file(path).entries["local_variants"].values == ["A", "B"]


def test_section_conditions_and_conditional_required(sample_form):
    parent, target = sample_form.fields[:2]
    parent.field_type = FieldType.CHECKBOX
    parent.validation = []
    parent.required = False
    target.required = False
    target.required_conditions = [ConditionalRule(field_id=parent.id, value=True, action="require")]
    for field in sample_form.fields[2:]:
        field.required = False
    assert not FormValidator().values(sample_form, {parent.id: False})
    assert any(i.field_id == target.id for i in FormValidator().values(sample_form, {parent.id: True}))


def test_group_and_section_cycles(sample_form):
    section = sample_form.sections[0]
    section.conditions = [ConditionalRule(field_id=sample_form.fields[0].id, value="x")]
    with pytest.raises(ValidationError):
        Form.model_validate(sample_form.model_dump())
    section.conditions = []
    sample_form.groups = [FieldGroup(id="g", title="A", section=section.id, parent_id="g")]
    with pytest.raises(ValidationError):
        Form.model_validate(sample_form.model_dump())


def test_optional_local_model_and_missing_fallback(tmp_path):
    source = document([Block(id="a", text="Informacja o ochronie danych i podstawie prawnej przetwarzania danych osobowych w urzędzie gminy dla mieszkańców.", page=1)])
    missing = assist(source, "")
    assert missing.warnings and missing.blocks[0].text == source.blocks[0].text
    model = train(
        [
            ("Informacja o ochronie danych podstawie prawnej danych osobowych urzędzie mieszkańców", "legal"),
            ("Wypełnij pola formularza wpisz dane czytelnie", "instruction"),
            ("DANE OSOBOWE", "heading"),
            ("Imię nazwisko numer", "text"),
        ]
    )
    path = tmp_path / "model.json"
    path.write_text(model.model_dump_json())
    analyzed = assist(source, path)
    assert analyzed.analysis["local_ai"]["proposals"][0]["block_id"] == "a"
    assert analyzed.blocks[0].text == source.blocks[0].text


def test_configured_adapter_is_strict_and_offline(sample_form):
    from formforge.mapping_config import ConfiguredAdapter, MappingConfig, Binding
    from jsonschema import ValidationError as SchemaError

    # This is a toy unit-test schema, explicitly NOT an official COI fixture.
    schema = {"type": "object", "properties": {"toyTitle": {"type": "string"}}, "required": ["toyTitle"], "additionalProperties": False}
    config = MappingConfig(enabled=True, bindings=[Binding(source="/title", target="/toyTitle")], verified_fixture_ids=["toy-unit-test-not-COI"])
    adapter = ConfiguredAdapter(config, schema)
    payload = adapter.map(sample_form)
    adapter.validate(payload)
    assert set(payload) == {"toyTitle"}
    with pytest.raises(SchemaError):
        adapter.validate({**payload, "extra": True})
    with pytest.raises(ValueError):
        ConfiguredAdapter(config, {"$ref": "https://example.invalid/schema"})
    with pytest.raises(ValueError):
        ConfiguredAdapter(config, {"$dynamicRef": "https://example.invalid/schema"})
    with pytest.raises(ValueError):
        ConfiguredAdapter(MappingConfig(), schema)


def test_ai_mode_api_is_local_and_validated(client):
    source = Path(__file__).resolve().parents[1] / "demo_samples/zezwolenie.docx"
    response = client.post(
        "/api/v1/forms/convert?analysis_mode=local-ai-assisted",
        files={"file": (source.name, source.read_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["document"]["analysis"]["local_ai"]["model"] == "formforge-naive-bayes-v1"
    assert result["form"]["confidence_semantics"] == "heuristic_score_not_calibrated_probability"
    assert client.post("/api/v1/forms/convert?analysis_mode=remote-llm", files={"file": (source.name, source.read_bytes())}).status_code == 422


def test_section_visibility_values(sample_form):
    from formforge.models import Section

    parent, target = sample_form.fields[:2]
    parent.field_type = FieldType.CHECKBOX
    parent.required = False
    parent.validation = []
    for field in sample_form.fields[2:]:
        field.required = False
    section = Section(id="conditional_section", title="Warunkowa", page=target.page, order=len(sample_form.sections), conditions=[ConditionalRule(field_id=parent.id, value=True)])
    sample_form.sections.append(section)
    target.section = section.id
    target.required = True
    validated = Form.model_validate(sample_form.model_dump())
    assert not FormValidator().values(validated, {parent.id: False})
    assert any(i.field_id == target.id and i.code == "required" for i in FormValidator().values(validated, {parent.id: True}))
