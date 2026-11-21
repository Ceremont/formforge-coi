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


def review(form, issues, coi):
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
    return {
        "counts": {
            "fields": len(form.fields),
            "sections": len(form.sections),
            "pages": len(form.pages),
            "dependencies": sum(len(f.conditions) + len(f.required_conditions) for f in form.fields) + sum(len(s.conditions) for s in form.sections),
            "dictionaries": len(form.dictionaries),
            "review_fields": sum(f.requires_review for f in form.fields),
            **{level.lower(): counts[level] for level in ["ERROR", "WARNING", "INFO"]},
        },
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
