"""Reviewable diagnostics; never equate local JSON validity with field accuracy."""

from collections import Counter

RECOMMENDATIONS = {
    "requires_review": "Porównaj etykietę, typ i reguły ze wskazanym fragmentem źródła; popraw je w edytorze.",
    "missing_options": "Dodaj warianty lub przypisz sprawdzony słownik w edytorze pola.",
    "required_conditions": "Potwierdź regułę. Oficjalny kontrakt nie opisuje dynamicznego REQUIRED; nie dodawaj własnej właściwości COI.",
    "invalid_link": "Popraw kolejność stron i sprawdź, czy każdy cel połączenia istnieje.",
    "nested_section": "Przenieś sekcję na poziom strony; sekcje COI nie mogą się zagnieżdżać.",
    "finish_info_only": "Na FINISH pozostaw wyłącznie INFO_SECTION; pola wejściowe przenieś na MAIN.",
    "missing_field_properties": "Uzupełnij obowiązkowe właściwości komponentu w edytorze i ponów walidację.",
}


def _predicates(expression):
    if expression is None:
        return 0
    return sum(_predicates(rule) for rule in expression.rules) if expression.op in ("and", "or") else 1


def metrics(form, export=None):
    """Configured predicates and exported states have different units; count both."""
    dependencies = Counter(source=0, standard_policy=0, manual=0, unverified=0)
    for node in [*form.fields, *form.sections]:
        for rule in [*node.conditions, *getattr(node, "required_conditions", [])]:
            if "ręcznie" in rule.evidence.lower():
                origin = "manual"
            elif rule.evidence:
                origin = "source"
            else:
                origin = node.coi.origin if node.coi.origin != "source" else "unverified"
            dependencies[origin] += 1
        # A source-backed field can receive a condition from the COI design policy.
        # Field provenance alone would incorrectly call that a source-detected rule.
        origin = "manual" if node.coi.origin == "manual" else "standard_policy" if node.coi.policy_rule or node.coi.origin == "standard_policy" else "source"
        dependencies[origin] += _predicates(node.coi.show_when) + _predicates(node.coi.read_only_when)
    from .coi_validation import fields_with_context

    components = [field for _, _, field, _ in fields_with_context(export or {})]
    states = Counter(state.get("type", "UNKNOWN") for field in components for state in field.get("states", []))
    containers = {"SECTION", "REPEATING_SECTION"}
    information = {"INFO_SECTION", "TEXT_BLOCK"}
    used = {f.coi.dictionary_name or (f.dictionary.id if f.dictionary else None) for f in form.fields} - {None}
    return {
        "model": {
            "fields": len(form.fields),
            "input_fields": sum(f.field_type != "information" for f in form.fields),
            "information_fields": sum(f.field_type == "information" for f in form.fields),
            "sections": len(form.sections),
            "pages": len(form.pages),
            "dictionaries_used": len(used),
            "dictionary_definitions": len(form.dictionaries),
        },
        "dependencies": {
            **dict(dependencies),
            "model_predicates": sum(dependencies.values()),
            "exported_states": sum(states.values()) if export is not None else None,
            "exported_by_type": dict(states),
            "units": "Model: configured comparison predicates, including section/COI expressions. Export: state objects on all recursive components; a state can combine several predicates. Rule evidence and COI policy metadata take precedence over field origin. Missing legacy evidence is unverified. COI expressions without a policy marker follow their declared node origin. Manual rules are separate from source and standard policy. Static readOnly and unconditional flow links are not dynamic states.",
        },
        "export": {
            "available": export is not None and "tabs" in export,
            "pages": len((export or {}).get("tabs", [])),
            "main_pages": sum(t.get("type") == "MAIN" for t in (export or {}).get("tabs", [])),
            "finish_pages": sum(t.get("type") == "FINISH" for t in (export or {}).get("tabs", [])),
            "sections": sum(f.get("type") in containers for f in components),
            "input_components": sum(f.get("type") not in containers | information for f in components),
            "information_components": sum(f.get("type") in information for f in components),
            "components_total": len(components),
            "dictionaries_used": len({f["dictionaryName"] for f in components if f.get("dictionaryName")}),
            "dictionary_bindings": sum(bool(f.get("dictionaryName")) for f in components),
        },
    }


def review(form, issues, coi, export=None):
    records = []
    seen = set()

    def add(issue, category):
        item = issue.model_dump() if hasattr(issue, "model_dump") else dict(issue)
        key = (item.get("code"), item.get("field_id"), item.get("path"), item.get("message"))
        if key in seen:
            return
        seen.add(key)
        code = item.get("code", "review")
        item.update(
            category=category,
            severity=item.get("severity", "warning").upper(),
            recommendation=RECOMMENDATIONS.get(code, "Sprawdź wskazany element w źródle i edytorze; następnie ponów lokalną walidację."),
        )
        records.append(item)

    for issue in issues:
        add(issue, "recognition")
    for issue in coi.get("schema_errors", []):
        add({**issue, "code": "schema", "severity": "error"}, "schema")
    for key in ["errors", "warnings", "review_items"]:
        for issue in coi.get(key, []):
            code = issue.get("code", "")
            category = (
                "links"
                if any(k in code for k in ["link", "flow", "reference", "cycle"])
                else "structure"
                if any(k in code for k in ["section", "finish", "grid", "tab"])
                else "dictionary"
                if "dictionary" in code
                else "business"
            )
            add(issue, category)
    if not form.fields:
        add({"severity": "error", "code": "no_fields", "message": "Nie wykryto pól wejściowych. Poprawny szkielet JSON nie oznacza odczytania dokumentu."}, "recognition")
    for field in form.fields:
        if field.coi.dictionary_name and not field.options:
            add(
                {
                    "severity": "info",
                    "code": "dictionary_values_remote",
                    "field_id": field.id,
                    "message": "Pełne wartości słownika udostępnia platforma COI; lokalny katalog zawiera jego opis.",
                },
                "dictionary",
            )
    add({"severity": "info", "code": "import_unverified", "message": "Nie przeprowadzono importu na rzeczywistej platformie COI."}, "platform")
    counts = Counter(i["severity"] for i in records)
    measured = metrics(form, export)
    return {
        "counts": {
            "fields": len(form.fields),
            "sections": len(form.sections),
            "pages": len(form.pages),
            "dependencies": measured["dependencies"]["model_predicates"],
            "exported_states": measured["dependencies"]["exported_states"],
            "dictionaries": measured["model"]["dictionaries_used"],
            "review_fields": sum(not f.coi.confirmed and (f.requires_review or f.confidence < 0.8 or f.coi.origin == "standard_policy") for f in form.fields),
            **{level.lower(): counts[level] for level in ["ERROR", "WARNING", "INFO"]},
        },
        "metrics": measured,
        "checks": {
            "schema_valid": coi.get("schema_valid", False),
            "business_rules_valid": coi.get("business_rules_valid", False),
            "compatibility_profile_valid": coi.get("compatibility_profile_valid", False),
            "actual_import_verified": False,
            "completeness_verified": False,
        },
        "diagnostics": records,
        "unsupported_features": coi.get("unsupported_features", []),
        "score_semantics": "Nie skalibrowano prawdopodobieństwa poprawności. Liczby opisują elementy i kontrole, a nie procent dokładności.",
    }
