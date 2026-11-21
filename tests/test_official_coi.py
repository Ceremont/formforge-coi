import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator
from formforge.coi_mapper import export_bundle
from formforge.coi_models import FormDefinition
from formforge.coi_validation import fields_with_context, schema, validate_coi
from formforge.config import Settings
from formforge.models import COIExpression, FieldGroup
from formforge.pipeline import convert

ROOT = Path(__file__).resolve().parents[1]


def test_schema_is_unchanged_and_insufficient():
    original = next((ROOT / "reference/coi-official/spec").glob("importowany*.json"))
    assert original.read_bytes() == (ROOT / "formforge/data/coi_schema.json").read_bytes()
    assert Draft202012Validator(schema()).is_valid({})
    assert not validate_coi({})["valid"]


@pytest.mark.parametrize("group", ["01", "05"])
def test_original_references_are_diagnosed_not_rewritten(group):
    original = json.loads(next((ROOT / "reference/coi-official/forms" / group).glob("*.json")).read_text())
    report = validate_coi(original)
    assert report["schema_valid"]
    assert not report["valid"]
    assert "finish_info_only" in {e["code"] for e in report["errors"]}


@pytest.mark.parametrize("group", ["01", "05"])
@pytest.mark.parametrize("extension", ["pdf", "docx"])
def test_reference_sources_generate_official_configuration(group, extension):
    source = next(p for p in (ROOT / "reference/coi-official/forms" / group).iterdir() if p.suffix.lower() == "." + extension and "wizualizac" not in p.name)
    result = convert(source, "unseen." + extension, extension, Settings())
    payload = result["export"]
    FormDefinition.model_validate(payload)
    assert result["coi_validation"]["valid"]
    assert payload["tabs"][-1]["questions"][0]["field"]["type"] == "INFO_SECTION"
    assert not result["coi_validation"]["target_import_verified"]
    assert result["coi_validation"]["requires_confirmation"]
    assert result["normalization"]["reference_json_used_at_runtime"] is False
    assert any(f.coi.origin == "standard_policy" for f in __import__("formforge.models", fromlist=["Form"]).Form.model_validate(result["form"]).fields)


def test_preview_api_remains_explicitly_available(client, sample_form):
    result = client.post("/api/v1/forms/validate", json={"form": sample_form.model_dump(mode="json"), "export_format": "preview"})
    assert result.status_code == 200
    assert result.json()["export"]["format"] == "formforge-preview"
    assert client.get("/api/v1/coi/schema").json() == schema()


@pytest.mark.parametrize(
    "change,code", [("link", "invalid_link"), ("nested", "nested_section"), ("finish", "finish_info_only"), ("grid", "invalid_grid"), ("properties", "missing_field_properties")]
)
def test_business_constraints_beyond_schema(sample_form, change, code):
    payload, _ = export_bundle(sample_form)
    field = payload["tabs"][0]["questions"][0]["field"]
    if change == "link":
        payload["flow"]["links"][0]["target"] = str(uuid4())
    elif change == "nested":
        field["repeatingSectionGrid"][0]["field"]["type"] = "SECTION"
    elif change == "finish":
        payload["tabs"][-1]["questions"][0]["field"]["type"] = "TEXT_FIELD"
    elif change == "grid":
        field["repeatingSectionGrid"][0]["x"] = 2
    else:
        del field["readOnly"]
    report = validate_coi(payload)
    assert not report["valid"]
    assert code in {e["code"] for e in report["errors"]}


def test_legacy_grid_spelling_accepted_canonical_serialization(sample_form):
    payload, _ = export_bundle(sample_form)
    for _, _, f, _ in list(fields_with_context(payload)):
        f["repetingSectionGrid"] = f.pop("repeatingSectionGrid")
    assert validate_coi(payload)["valid"]
    assert "repetingSectionGrid" not in json.dumps(FormDefinition.model_validate(payload).model_dump(mode="json"))


def test_repeating_section_dynamic_states_and_jsonata(sample_form):
    fields = sample_form.fields[:2]
    fields[0].field_type = "radio"
    fields[0].options = ["Tak", "Nie"]
    fields[1].coi.show_when = COIExpression(op="equals", field_id=fields[0].id, value="Tak")
    fields[1].section = fields[0].section
    fields[1].page = fields[0].page
    sample_form.fields = fields
    sample_form.sections = [s for s in sample_form.sections if s.id == fields[0].section]
    sample_form.groups = [FieldGroup(id="g_repeat", title="Wiersze", section=fields[0].section, repeat_key="items")]
    for f in fields:
        f.group_id = "g_repeat"
    payload, report = export_bundle(sample_form)
    assert report["valid"], report["errors"]
    assert payload["tabs"][0]["questions"][0]["field"]["type"] == "REPEATING_SECTION"
    states = [s for _, _, f, _ in fields_with_context(payload) for s in f["states"]]
    assert "$repeatingSectionIndex" in states[0]["query"]
    assert report["review_items"]


@pytest.mark.parametrize("payload", [{"tabs": "bad"}, {"tabs": [3]}, {"tabs": [{"questions": [{"field": {"states": [None]}}]}]}, {"flow": {"links": [None]}}])
def test_malformed_official_input_is_a_report_not_500(client, payload):
    response = client.post("/api/v1/forms/coi-validate", json=payload)
    assert response.status_code == 200
    assert not response.json()["valid"]


def test_semantic_comparison_ignores_uuid_and_storage_order(sample_form):
    from formforge.coi_compare import compare

    payload, _ = export_bundle(sample_form)
    other = copy.deepcopy(payload)
    ids = {}
    for tab in other["tabs"]:
        ids[tab["id"]] = str(uuid4())
        tab["id"] = ids[tab["id"]]
        tab["questions"].reverse()
    for _, _, f, _ in fields_with_context(other):
        f["id"] = str(uuid4())
        f["repeatingSectionGrid"].reverse()
    for link in other["flow"]["links"]:
        link.update(id=str(uuid4()), source=ids[link["source"]], target=ids[link["target"]])
    metrics = compare(payload, other)
    assert metrics["field_f1"] == metrics["structural_similarity"] == 1
