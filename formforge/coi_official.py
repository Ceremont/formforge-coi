"""Content-driven mapping to the real COI FormDefinition, with a review sidecar."""

import json
import re
from uuid import NAMESPACE_URL, uuid5
from .coi_models import FormDefinition
from .coi_validation import validate_coi
from .layout_analyzer import fold

TYPES = {
    "text": "TEXT_FIELD",
    "email": "TEXT_FIELD",
    "phone": "TEXT_FIELD",
    "pesel": "TEXT_FIELD",
    "nip": "TEXT_FIELD",
    "regon": "TEXT_FIELD",
    "postal_code": "TEXT_FIELD",
    "address": "TEXT_FIELD",
    "textarea": "TEXTAREA",
    "number": "NUMBER",
    "date": "DATEPICKER",
    "checkbox": "CHECKBOX",
    "radio": "RADIO",
    "select": "SELECT",
    "attachment": "FILE_UPLOADER",
    "information": "TEXT_BLOCK",
    "consent": "CONSENT_SECTION",
}
VALIDATION = {"required": "REQUIRED", "email": "EMAIL", "pesel": "PESEL", "nip": "NIP", "regon": "REGON", "postal_code": "ZIP_CODE"}


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", fold(text)).strip("_")[:100] or "pole"


class COIFormAdapter:
    def __init__(self):
        self.review = []
        self.locations = {}
        self.provenance = {}

    def map(self, form):
        self.review = []
        self.locations = {}
        self.provenance = {}

        def uid(key):
            return str(uuid5(NAMESPACE_URL, form.id + "/" + key))

        def base(key, kind, title):
            return {
                "id": uid(key),
                "type": kind,
                "techName": slug(title) + "_" + slug(key)[-15:],
                "title": title,
                "description": "",
                "options": [],
                "validation": [],
                "readOnly": False,
                "repeatingSectionGrid": [],
                "states": [],
                "questionOrder": 0,
                "tooltipMessage": "",
            }

        def question(field, y, rows=1):
            return {"x": 0, "y": y, "rows": rows, "cols": 3, "field": field}

        themes = {}
        for section in sorted(form.sections, key=lambda s: s.order):
            title = section.coi.tab or next(p.title for p in form.pages if p.id == section.page)
            themes.setdefault(title, []).append(section)
        tabs = []
        containers = []
        for title, sections in themes.items():
            tab = {"id": uid("tab/" + title), "title": title[:255] or "Dane", "type": "MAIN", "questions": []}
            tabs.append(tab)
            for section in sections:
                source_fields = sorted([f for f in form.fields if f.section == section.id], key=lambda f: f.order)
                groups = [g for g in form.groups if g.section == section.id]
                group_ids = {g.id for g in groups}
                partitions = [(section.id, section.title, "SECTION", [f for f in source_fields if f.group_id not in group_ids], section.instructions)]
                for group in groups:
                    members = [f for f in source_fields if f.group_id == group.id]
                    if members:
                        kind = "REPEATING_SECTION" if group.repeat_key else "SECTION"
                        partitions.append((group.id, group.title, kind, members, []))
                        if group.repeat_key:
                            self.review.append({"code": "repeat_confirmation", "message": "Potwierdź, że tabela oznacza dynamiczną sekcję powtarzalną.", "field_id": group.id})
                for key, name, kind, members, instructions in partitions:
                    if not members and not instructions:
                        continue
                    container = base("section/" + key, kind, name)
                    children = []
                    y = 0
                    for index, text in enumerate(instructions):
                        if not text.strip():
                            continue
                        static = base(f"static/{key}/{index}", "TEXT_BLOCK", "")
                        static["description"] = text[:20000]
                        children.append(question(static, y))
                        y += 1
                    for field in members:
                        mapped = base("field/" + field.id, TYPES[field.field_type], field.label)
                        mapped["techName"] = slug(field.label) + "_" + field.id[-10:]
                        mapped["description"] = field.help_text
                        mapped["readOnly"] = field.coi.read_only
                        mapped["validation"] = list(
                            dict.fromkeys((["REQUIRED"] if field.required else []) + [VALIDATION[r.kind] for r in field.validation if r.kind in VALIDATION])
                        )
                        if mapped["type"] != "TEXT_FIELD":
                            mapped["validation"] = [v for v in mapped["validation"] if v == "REQUIRED"]
                        if field.field_type in ("email", "pesel", "nip", "regon", "postal_code") and mapped["type"] == "TEXT_FIELD":
                            value = VALIDATION.get(field.field_type)
                            if value and value not in mapped["validation"]:
                                mapped["validation"].append(value)
                        if field.field_type in ("select", "radio", "checkbox"):
                            if field.coi.dictionary_name:
                                mapped["dictionaryName"] = field.coi.dictionary_name
                                mapped["searchEnabled"] = True
                                if field.coi.dictionary_name.startswith("TERYT"):
                                    mapped["multiLevelTree"] = True
                            else:
                                values = field.options or (field.dictionary.values if field.dictionary else [])
                                if field.field_type == "checkbox" and not values:
                                    values = [field.label]
                                mapped["options"] = [{"id": value, "name": value, "techName": slug(value) + "_" + str(i)} for i, value in enumerate(values)]
                                if field.dictionary and field.dictionary.source != "official":
                                    self.review.append(
                                        {
                                            "code": "proposed_dictionary",
                                            "message": "Opcje pochodzą z dokumentu lub propozycji, nie z potwierdzonego słownika COI.",
                                            "field_id": field.id,
                                        }
                                    )
                        default = field.coi.default_value if field.coi.default_value is not None else form.initial_data.get(field.id)
                        if default is not None:
                            if mapped["type"] in ("RADIO", "SELECT", "CHECKBOX") and not isinstance(default, list):
                                default = [str(default)]
                            mapped["defaultValue"] = default
                        if field.coi.default_value_type:
                            mapped["defaultValueType"] = field.coi.default_value_type
                            mapped["readOnly"] = True
                        if field.field_type == "consent":
                            mapped["consentSectionConfig"] = {
                                "consents": [{"description": field.help_text or field.label, "required": field.required or field.coi.consent_required}],
                                "files": [],
                            }
                            mapped["validation"] = []
                        if field.field_type == "information":
                            mapped["description"] = field.help_text or field.label
                        mapped["questionOrder"] = len(children)
                        rows = 3 if field.field_type == "textarea" else 1
                        children.append(question(mapped, y, rows))
                        y += rows
                        self.locations[field.id] = {"tab": tab, "container": container, "field": mapped, "repeating": kind == "REPEATING_SECTION"}
                        self.provenance[mapped["id"]] = {
                            "internal_field_id": field.id,
                            "origin": field.coi.origin,
                            "policy_rule": field.coi.policy_rule,
                            "requires_confirmation": not field.coi.confirmed and (field.requires_review or field.coi.origin == "standard_policy"),
                            "source_reference": field.source_reference.model_dump(mode="json"),
                        }
                        for rule in field.validation:
                            if rule.kind not in VALIDATION and rule.kind != "date" and not (field.field_type == "pesel" and rule.kind in ("min_length", "max_length")):
                                self.review.append(
                                    {
                                        "code": "unsupported_validation",
                                        "message": f"COI nie określa serializacji reguły {rule.kind}={rule.value}. Zachowano ją w modelu wewnętrznym.",
                                        "field_id": field.id,
                                    }
                                )
                        if field.required_conditions:
                            self.review.append(
                                {
                                    "code": "conditional_required_unsupported",
                                    "message": "Specyfikacja nie określa dynamicznego REQUIRED. Reguła pozostaje w modelu i wymaga potwierdzenia.",
                                    "field_id": field.id,
                                }
                            )
                    container["repeatingSectionGrid"] = children
                    container["questionOrder"] = len(tab["questions"])
                    top_y = sum(q["rows"] for q in tab["questions"])
                    tab["questions"].append(question(container, top_y, max(1, y + 1)))
                    containers.append((section, container))
            if not tab["questions"]:
                section = base("empty/" + title, "SECTION", "Informacje")
                info = base("empty-text/" + title, "TEXT_BLOCK", "")
                info["description"] = "Nie wykryto pól. Sprawdź źródło dokumentu."
                section["repeatingSectionGrid"] = [question(info, 0)]
                tab["questions"] = [question(section, 0, 2)]
        for field in form.fields:
            location = self.locations.get(field.id)
            if not location:
                continue
            conditions = []
            if field.coi.show_when:
                conditions.append(self.expression(field.coi.show_when))
            conditions.extend(self.condition(c) for c in field.conditions)
            conditions = [q for q in conditions if q]
            if conditions:
                location["field"]["states"].append({"type": "SHOW", "query": " and ".join("(" + q + ")" for q in conditions)})
            if field.coi.read_only_when:
                location["field"]["states"].append({"type": "READ_ONLY", "query": self.expression(field.coi.read_only_when)})
        for section, container in containers:
            conditions = ([self.expression(section.coi.show_when)] if section.coi.show_when else []) + [self.condition(c) for c in section.conditions]
            conditions = [q for q in conditions if q]
            if conditions:
                container["states"] = [{"type": "SHOW", "query": " and ".join("(" + q + ")" for q in conditions)}]
        finish = base("finish-info", "INFO_SECTION", "Podgląd")
        finish["description"] = "Zanim przejdziesz do wyboru sposobu podpisu, sprawdź dane na podglądzie. Jeśli zobaczysz błędy, wróć do edycji."
        tabs.append({"id": uid("finish"), "title": "Strona końcowa", "type": "FINISH", "questions": [question(finish, 0)]})
        links = [{"id": uid(f"link/{a['id']}/{b['id']}"), "source": a["id"], "target": b["id"]} for a, b in zip(tabs, tabs[1:])]
        payload = {"title": form.title[:255], "tabs": tabs, "flow": {"links": links}}
        return FormDefinition.model_validate(payload).model_dump(mode="json", exclude_none=True)

    def answer_path(self, identifier):
        loc = self.locations.get(identifier)
        if not loc:
            raise ValueError("Condition points to unmapped field")

        def quote(x):
            return json.dumps(x, ensure_ascii=False)

        prefix = f"tabs[{quote(loc['tab']['title'])} in title].questions[{quote(loc['container']['techName'])} in field.techName].field"
        if loc["repeating"]:
            return prefix + f".__userAnswer[$repeatingSectionIndex][{quote(loc['field']['techName'])} in fieldTechName].answers"
        return prefix + f".repeatingSectionGrid[{quote(loc['field']['techName'])} in field.techName].field.__userAnswer"

    def condition(self, condition):
        value = condition.value
        if isinstance(value, bool):
            field = self.locations[condition.field_id]["field"]
            options = field.get("options") or []
            if not options:
                self.review.append(
                    {
                        "code": "boolean_condition_unsupported",
                        "message": "Warunek logiczny odwołuje się do pola bez jawnej opcji wyboru. Zachowano regułę w modelu; popraw typ, słownik lub wartość warunku w edytorze.",
                        "field_id": condition.field_id,
                    }
                )
                return ""
            option = options[0]["id"]
            query = json.dumps(option, ensure_ascii=False) + " in " + self.answer_path(condition.field_id)
            return query if (value == (condition.operator == "equals")) else "$not(" + query + ")"
        query = json.dumps(value, ensure_ascii=False) + " in " + self.answer_path(condition.field_id)
        return "$not(" + query + ")" if condition.operator == "not_equals" else query

    def expression(self, expression):
        if expression.op in ("and", "or"):
            return (" " + expression.op + " ").join("(" + self.expression(r) + ")" for r in expression.rules)
        from .models import ConditionalRule

        return self.condition(ConditionalRule(field_id=expression.field_id, value=expression.value, operator=expression.op))

    def validate(self, payload):
        report = validate_coi(payload)
        if not report["valid"]:
            raise ValueError("Invalid official COI configuration: " + str(report["errors"][:3]))

    def report(self, payload):
        report = validate_coi(payload)
        report["review_items"] = self.review
        report["provenance"] = self.provenance
        report["requires_confirmation"] = any(v["requires_confirmation"] for v in self.provenance.values()) or bool(self.review)
        report["status"] = "valid_requires_review" if report["valid"] and report["requires_confirmation"] else "valid_configuration" if report["valid"] else "invalid_configuration"
        report["unsupported_features"] = [v for v in self.review if v["code"].endswith("unsupported") or v["code"] == "unsupported_validation"]
        return report
