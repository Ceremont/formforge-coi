"""Raw schema, recursive compatibility and technical/business checks separately."""

import json
import re
from functools import lru_cache
from pathlib import Path
from uuid import UUID
from jsonschema import Draft202012Validator
from pydantic import ValidationError
from .coi_models import FormDefinition

CONTAINERS = {"SECTION", "REPEATING_SECTION"}
INPUTS = {"TEXT_FIELD", "TEXTAREA", "NUMBER", "SELECT", "RADIO", "CHECKBOX", "DATEPICKER", "FILE_UPLOADER", "CONSENT_SECTION"}
VALIDATORS = {"REQUIRED", "EMAIL", "PESEL", "NIP", "REGON", "ZIP_CODE", "EPUAP", "ADE", "SERIAL_NUMBER_ID_CARD"}
DICTIONARIES = {"Kraje", "TERYT_DOWODOWY", "TERYT_4G_DOWODOWY", "Województwo", "Powiat", "Gmina", "Miejscowość", "Numery kierunkowe"}
INITIAL_ATTRIBUTES = {
    "MLPZ": set(
        "name secondName surname pesel phoneNumber email country voivodeship district community place postCode street building apartment institutionName descriptiveOrganizationName".split()
    ),
    "PESEL": set(
        "pesel name surname birthDate citizenship motherName birthPlace motherSurname sex fatherName secondName birthCountry foreignBirthUSC familyName fatherSurname maritalStatus".split()
    ),
    "PESEL_ADDRESS": set(
        prefix + suffix
        for prefix in ("temporaryAddress", "permanentAddress")
        for suffix in ("Voivodeship", "District", "Community", "Place", "StreetType", "Street", "HouseNumber", "ApartmentNumber", "PostalCode")
    ),
}


@lru_cache
def schema():
    return json.loads((Path(__file__).parent / "data/coi_schema.json").read_text())


def nested(field):
    return field.get("repeatingSectionGrid", field.get("repetingSectionGrid", []))


def fields_with_context(payload):
    def descend(tab, parent, questions, prefix, depth=0):
        if depth > 16:
            return
        for i, q in enumerate(questions):
            f = q.get("field", {})
            path = f"{prefix}/{i}"
            yield tab, parent, f, path
            yield from descend(tab, f, nested(f), path + "/field/repeatingSectionGrid", depth + 1)

    for ti, tab in enumerate(payload.get("tabs", [])):
        yield from descend(tab, None, tab.get("questions", []), f"tabs/{ti}/questions")


def validate_coi(payload):
    errors = []
    warnings = []

    def issue(code, message, path="", severity="error"):
        (errors if severity == "error" else warnings).append({"code": code, "message": message, "path": path, "severity": severity})

    raw = list(Draft202012Validator(schema()).iter_errors(payload))
    schema_errors = [{"path": "/".join(map(str, e.absolute_path)), "message": e.message} for e in raw]

    def safe_questions(items, depth=0):
        if not isinstance(items, list) or len(items) > 5000 or depth > 16:
            return False
        for q in items:
            if not isinstance(q, dict) or not isinstance(q.get("field"), dict):
                return False
            f = q["field"]
            if any(not isinstance(f.get(k, ""), str) for k in ("id", "type", "techName", "title")):
                return False
            if not isinstance(f.get("states", []), list) or any(
                not isinstance(s, dict) or not isinstance(s.get("query", ""), str) or len(s.get("query", "")) > 8000 for s in f.get("states", [])
            ):
                return False
            if "consentSectionConfig" in f and not isinstance(f["consentSectionConfig"], dict):
                return False
            if not safe_questions(nested(f), depth + 1):
                return False
        return True

    tabs_shape = payload.get("tabs", [])
    flow_shape = payload.get("flow", {})
    safe = (
        isinstance(tabs_shape, list)
        and len(tabs_shape) <= 100
        and all(isinstance(t, dict) and isinstance(t.get("id", ""), str) and isinstance(t.get("title", ""), str) and safe_questions(t.get("questions", [])) for t in tabs_shape)
    )
    safe = (
        safe
        and isinstance(flow_shape, dict)
        and isinstance(flow_shape.get("links", []), list)
        and all(isinstance(link, dict) and all(isinstance(link.get(k, ""), str) for k in ("id", "source", "target")) for link in flow_shape.get("links", []))
    )
    if not safe:
        return {
            "schema_valid": not raw,
            "schema_errors": schema_errors,
            "compatibility_profile_valid": False,
            "business_rules_valid": False,
            "valid": False,
            "errors": [{"code": "invalid_structure", "message": "Nieprawidłowe typy lub rozmiar struktury COI.", "path": "", "severity": "error"}],
            "warnings": [],
            "target_import_verified": False,
        }
    try:
        FormDefinition.model_validate(payload)
        profile_valid = True
    except ValidationError as exc:
        profile_valid = False
        for e in exc.errors():
            issue("compatibility_model", e["msg"], "/".join(map(str, e["loc"])))
    tabs = payload.get("tabs", [])
    ids = [t.get("id") for t in tabs]
    all_ids = []
    if len(tabs) < 2:
        issue("minimum_tabs", "Formularz wymaga co najmniej dwóch stron.")
    if not tabs or tabs[-1].get("type") != "FINISH" or sum(t.get("type") == "FINISH" for t in tabs) != 1:
        issue("finish_page", "Wymagana dokładnie jedna końcowa strona FINISH.")

    def grid_check(questions, path):
        rectangles = []
        names = []
        for q in questions:
            f = q.get("field", {})
            names.append(f.get("techName"))
            if all(isinstance(q.get(k), int) and not isinstance(q.get(k), bool) for k in ("x", "y", "rows", "cols")):
                x, y, w, h = q["x"], q["y"], q["cols"], q["rows"]
                if x < 0 or y < 0 or w < 1 or h < 1 or x + w > 3:
                    issue("invalid_grid", "Nieprawidłowe współrzędne siatki.", str(f.get("id")))
                for a, b, c, d in rectangles:
                    if x < a + c and x + w > a and y < b + d and y + h > b:
                        issue("grid_overlap", "Komponenty nakładają się w siatce.", str(f.get("id")))
                rectangles.append((x, y, w, h))
        if len(names) != len(set(names)):
            issue("duplicate_tech_name", "Nazwa techniczna musi być unikalna w swoim kontenerze.", path)

    for tab in tabs:
        all_ids.append(tab.get("id"))
        if not tab.get("questions"):
            issue("empty_tab", "Każda strona musi mieć komponent.", str(tab.get("id")))
        for question in tab.get("questions", []):
            f = question.get("field", {})
            if tab.get("type") == "FINISH":
                if f.get("type") != "INFO_SECTION":
                    issue("finish_info_only", "Na FINISH dozwolone jest wyłącznie INFO_SECTION.", str(f.get("id")))
            elif f.get("type") not in CONTAINERS:
                issue("input_outside_section", "Komponent MAIN musi należeć do SECTION lub REPEATING_SECTION.", str(f.get("id")))
        grid_check(tab.get("questions", []), str(tab.get("id")))
    contexts = list(fields_with_context(payload))
    by_section = {(t.get("title"), f.get("techName")): f for t, parent, f, _ in contexts if parent is None}
    for tab, parent, f, path in contexts:
        all_ids.append(f.get("id"))
        grid_check(nested(f), path)
        required = {"id", "type", "techName", "title", "description", "options", "validation", "readOnly", "states", "questionOrder", "tooltipMessage"}
        absent = required - set(f)
        if "repeatingSectionGrid" not in f and "repetingSectionGrid" not in f:
            absent.add("repeatingSectionGrid")
        if absent:
            issue("missing_field_properties", "Brak właściwości komponentu: " + ", ".join(sorted(absent)), path)
        if f.get("type") not in CONTAINERS and nested(f):
            issue("children_outside_section", "Tylko sekcja może zawierać komponenty.", path)
        if "repetingSectionGrid" in f:
            issue("legacy_grid_spelling", "Wejście używa repetingSectionGrid; eksport używa repeatingSectionGrid.", path, "warning")
        if parent and f.get("type") in CONTAINERS:
            issue("nested_section", "Sekcje nie mogą zawierać sekcji.", path)
        if f.get("type") in CONTAINERS and (not f.get("title") or not nested(f)):
            issue("empty_section", "Sekcja wymaga tytułu i co najmniej jednego komponentu.", path)
        if f.get("type") in INPUTS and "validation" not in f:
            issue("requiredness_missing", "Brak jawnej konfiguracji obligatoryjności validation.", path)
        validation = f.get("validation", [])
        if not isinstance(validation, list):
            issue("validation_array", "validation musi być tablicą.", path)
        elif any(not isinstance(v, str) or v not in VALIDATORS for v in validation):
            issue("unsupported_validator", "Nieobsługiwany kod walidacji.", path)
        if f.get("type") != "TEXT_FIELD" and isinstance(validation, list) and any(v != "REQUIRED" for v in validation):
            issue("validator_type", "Ten komponent dopuszcza tylko REQUIRED.", path)
        if f.get("dictionaryName"):
            if f.get("type") not in {"SELECT", "RADIO", "CHECKBOX"}:
                issue("dictionary_type", "Słownik jest dozwolony tylko w polu wyboru.", path)
            if f.get("options"):
                issue("dictionary_options", "Opcje muszą być puste przy dictionaryName.", path)
            if f["dictionaryName"] not in DICTIONARIES:
                issue("dictionary_unknown", "Słownik wymaga potwierdzenia w katalogu COI.", path, "warning")
        if f.get("type") in ("SELECT", "RADIO", "CHECKBOX") and not f.get("dictionaryName") and not f.get("options"):
            issue("missing_options", "Pole wyboru nie zawiera opcji ani słownika.", path)
        if f.get("defaultValueType") == "EXTERNAL_SYSTEM" and not f.get("readOnly"):
            issue("registry_read_only", "Dane inicjalne z rejestru muszą być readOnly.", path)
        if f.get("defaultValueType") == "EXTERNAL_SYSTEM":
            binding = f.get("defaultValue", "")
            pieces = binding.split(".") if isinstance(binding, str) else []
            if len(pieces) != 2 or pieces[1] not in INITIAL_ATTRIBUTES.get(pieces[0], set()):
                issue("initial_binding", "Nieznane źródło lub atrybut danych inicjalnych.", path)
        if f.get("type") == "INFO_SECTION" and not f.get("description"):
            issue("info_description", "INFO_SECTION wymaga opisu.", path)
        if f.get("type") == "CONSENT_SECTION" and not f.get("consentSectionConfig", {}).get("consents"):
            issue("consent_configuration", "Brak konfiguracji zgód.", path)
        for state in f.get("states", []):
            query = state.get("query", "")
            if f.get("type") in CONTAINERS and state.get("type") != "SHOW":
                issue("section_state", "Sekcja dopuszcza wyłącznie SHOW.", path)
            try:
                import jsonata

                jsonata.Jsonata(query, timeout=200, stack=100)
            except Exception:
                issue("invalid_jsonata", "Nieprawidłowa składnia JSONata.", path)
            pattern = r"tabs\[([\x27\x22])(.*?)\1\s*in title\]\.questions\[([\x27\x22])(.*?)\3\s*in field.techName\]"
            for match in re.finditer(pattern, query):
                container = by_section.get((match.group(2), match.group(4)))
                if container is None:
                    issue("jsonata_reference", "JSONata wskazuje nieistniejącą stronę lub sekcję.", path)
                else:
                    tail = query[match.end() :]
                    child = re.match(r"\.field\.repeatingSectionGrid\[([\x27\x22])(.*?)\1\s*in field.techName\]", tail)
                    if child and child.group(2) not in {q["field"].get("techName") for q in nested(container)}:
                        issue("jsonata_field_reference", "JSONata wskazuje nieistniejące pole.", path)
    links = payload.get("flow", {}).get("links", [])
    edges = {identifier: [] for identifier in ids}
    for link in links:
        all_ids.append(link.get("id"))
        if link.get("source") not in ids or link.get("target") not in ids:
            issue("invalid_link", "Przepływ wskazuje nieistniejącą stronę.", str(link.get("id")))
        elif link.get("source") == link.get("target"):
            issue("self_link", "Przejście do tej samej strony.", str(link.get("id")))
        else:
            edges[link["source"]].append(link["target"])
    if tabs:
        seen = set()
        pending = [ids[0]]
        while pending:
            node = pending.pop()
            if node in seen:
                continue
            seen.add(node)
            pending.extend(edges.get(node, []))
        if seen != set(ids):
            issue("unreachable_tabs", "Nie wszystkie strony są osiągalne.")
        if edges.get(ids[-1]):
            issue("finish_outgoing", "FINISH nie może mieć przejścia wychodzącego.")
        order = {identifier: i for i, identifier in enumerate(ids)}
        if any(order.get(target, -1) <= order.get(source, -1) for source, targets in edges.items() for target in targets):
            issue("flow_cycle", "Przepływ musi prowadzić do przodu bez cykli.")
    if len(all_ids) != len(set(all_ids)):
        issue("duplicate_id", "Powtórzony identyfikator.")
    for identifier in all_ids:
        try:
            UUID(str(identifier))
        except ValueError, TypeError:
            issue("non_uuid", "Identyfikator nie jest UUID.", str(identifier))
    return {
        "schema_valid": not raw,
        "schema_errors": schema_errors,
        "compatibility_profile_valid": profile_valid,
        "business_rules_valid": not errors,
        "valid": not raw and profile_valid and not errors,
        "errors": errors,
        "warnings": warnings,
        "schema_profile": "published unchanged + recursive compatibility + technical rules",
        "grid_key": "repeatingSectionGrid",
        "target_import_verified": False,
    }
