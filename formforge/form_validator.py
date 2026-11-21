import re
from datetime import date
from decimal import Decimal, InvalidOperation

from .models import FieldType, Form, Issue


def valid_pesel(value: str) -> bool:
    if not re.fullmatch(r"[0-9]{11}", value):
        return False
    if sum(int(v) * w for v, w in zip(value[:10], [1, 3, 7, 9, 1, 3, 7, 9, 1, 3])) % 10 != (10 - int(value[-1])) % 10:
        return False
    yy, mm, dd = int(value[:2]), int(value[2:4]), int(value[4:6])
    century = {0: 1900, 1: 2000, 2: 2100, 3: 2200, 4: 1800}.get(mm // 20)
    try:
        date(century + yy, mm % 20, dd)
        return True
    except TypeError, ValueError:
        return False


def is_visible(field, values, by_id, visiting=None):
    visiting = (visiting or set()) | {field.id}
    if not coi_expression_holds(field.coi.show_when, values, by_id, visiting):
        return False
    for condition in field.conditions:
        parent = by_id[condition.field_id]
        if parent.id in visiting or not is_visible(parent, values, by_id, visiting):
            return False
        value = values.get(parent.id, False if parent.field_type == FieldType.CHECKBOX else "")
        equal = value == condition.value
        if (condition.operator == "equals" and not equal) or (condition.operator == "not_equals" and equal):
            return False
    return True


def valid_identifier(text, kind):
    if kind == "nip":
        return bool(re.fullmatch(r"[0-9]{10}", text)) and sum(int(d) * w for d, w in zip(text[:9], [6, 5, 7, 2, 3, 4, 5, 6, 7])) % 11 == int(text[-1]) and len(set(text)) > 1
    if not re.fullmatch(r"(?:[0-9]{9}|[0-9]{14})", text) or len(set(text)) == 1:
        return False
    weights = [8, 9, 2, 3, 4, 5, 6, 7] if len(text) == 9 else [2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8]
    checksum = sum(int(d) * w for d, w in zip(text[:-1], weights)) % 11
    return (0 if checksum == 10 else checksum) == int(text[-1]) and (len(text) == 9 or valid_identifier(text[:9], "regon"))


class FormValidator:
    def inspect(self, form: Form) -> list[Issue]:
        issues = [Issue(severity="warning", code="coi_review", message="Eksport COI jest propozycją konfiguracji. Sprawdź zgodność, źródła i reguły w zakładce Zgodność z COI.")]
        for warning in form.warnings:
            issues.append(Issue(severity="warning", code="document_review", message=warning))
        for field in form.fields:
            if field.requires_review or field.confidence < 0.8:
                issues.append(Issue(severity="warning", code="requires_review", message="Sprawdź etykietę, typ i reguły pola.", field_id=field.id))
            if field.field_type in (FieldType.RADIO, FieldType.SELECT) and not field.options and not field.coi.dictionary_name:
                issues.append(Issue(severity="error", code="missing_options", message="Pole wyboru nie ma rozpoznanych opcji.", field_id=field.id))
        return issues

    def values(self, form: Form, values: dict) -> list[Issue]:
        issues = []
        section_conditions = {s.id: s.conditions for s in form.sections}
        sections = {s.id: s for s in form.sections}
        by_id = {}
        from .models import COIExpression

        for f in form.fields:
            rules = [r for r in (f.coi.show_when, sections[f.section].coi.show_when) if r]
            hints = f.coi.model_copy(update={"show_when": COIExpression(op="and", rules=rules) if rules else None})
            by_id[f.id] = f.model_copy(update={"conditions": f.conditions + section_conditions[f.section], "coi": hints})
        for unknown in values.keys() - by_id.keys():
            issues.append(Issue(severity="error", code="unknown_field", message="Nieznane pole w danych.", field_id=unknown))
        for original in form.fields:
            field = by_id[original.id]
            if field.field_type == FieldType.INFORMATION:
                continue
            if not is_visible(field, values, by_id):
                continue
            value = values.get(field.id)
            missing = (
                value is None or value == "" or isinstance(value, str) and not value.strip() or field.field_type in (FieldType.CHECKBOX, FieldType.CONSENT) and value is not True
            )
            required = field.required or any(r.kind == "required" for r in field.validation)
            if field.required_conditions:
                conditional = field.model_copy(update={"conditions": field.required_conditions})
                required = required or is_visible(conditional, values, by_id)
            if missing:
                if required:
                    issues.append(Issue(severity="error", code="required", message="To pole jest wymagane.", field_id=field.id))
                continue
            error = self._value_error(field, value)
            if error:
                issues.append(Issue(severity="error", code="invalid_value", message=error, field_id=field.id))
        return issues

    def _value_error(self, field, value):
        kind = field.field_type
        if kind in (FieldType.CHECKBOX, FieldType.CONSENT):
            return None if isinstance(value, bool) else "Wartość musi być logiczna."
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            return "Nieprawidłowy typ danych."
        text = str(value).strip()
        if kind == FieldType.NUMBER:
            try:
                number = Decimal(text.replace(",", "."))
                if not number.is_finite():
                    return "Podaj skończoną liczbę."
            except InvalidOperation:
                return "Podaj poprawną liczbę."
        if kind == FieldType.EMAIL and (len(text) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+", text)):
            return "Podaj poprawny adres e-mail."
        if kind == FieldType.PESEL and not valid_pesel(text):
            return "Nieprawidłowy PESEL (suma kontrolna lub data urodzenia)."
        if kind in (FieldType.NIP, FieldType.REGON) and not valid_identifier(text, kind.value):
            return f"Nieprawidłowy {kind.value.upper()} (długość lub suma kontrolna)."
        if kind == FieldType.PHONE and (not re.fullmatch(r"\+?[0-9 ()-]{7,25}", text) or not 7 <= len(re.sub(r"\D", "", text)) <= 15):
            return "Podaj poprawny numer telefonu."
        if kind == FieldType.POSTAL_CODE and not re.fullmatch(r"[0-9]{2}-[0-9]{3}", text):
            return "Kod pocztowy musi mieć format 00-000."
        if kind == FieldType.DATE:
            try:
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
                    return "Podaj datę w formacie RRRR-MM-DD."
                date.fromisoformat(text)
            except ValueError:
                return "Nieprawidłowa data."
        if kind in (FieldType.SELECT, FieldType.RADIO) and text not in field.options:
            return "Wybierz wartość ze słownika pola."
        for rule in field.validation:
            if rule.kind in ("min_length", "max_length") and rule.value is not None:
                limit = int(rule.value)
                if rule.kind == "min_length" and len(text) < limit or rule.kind == "max_length" and len(text) > limit:
                    return rule.message or f"Wymagana długość: {rule.kind} = {limit}."
            if rule.kind in ("min", "max") and rule.value is not None and kind == FieldType.NUMBER:
                if rule.kind == "min" and number < Decimal(str(rule.value)) or rule.kind == "max" and number > Decimal(str(rule.value)):
                    return rule.message or f"Przekroczono ograniczenie {rule.kind} = {rule.value}."
        # Validation rules can remain when an editor changes a field's type.
        for rule in field.validation:
            if rule.kind in ("email", "phone", "pesel", "nip", "regon", "postal_code", "date") and rule.kind != kind.value:
                synthetic = field.model_copy(update={"field_type": FieldType(rule.kind), "validation": []})
                error = self._value_error(synthetic, value)
                if error:
                    return error
        return None


def coi_expression_holds(expression, values, by_id=None, visiting=None):
    if expression is None:
        return True
    if expression.op == "and":
        return all(coi_expression_holds(r, values, by_id, visiting) for r in expression.rules)
    if expression.op == "or":
        return any(coi_expression_holds(r, values, by_id, visiting) for r in expression.rules)
    if by_id is not None:
        parent = by_id.get(expression.field_id)
        if not parent or parent.id in (visiting or set()) or not is_visible(parent, values, by_id, visiting):
            return False
    value = values.get(expression.field_id, "")
    if isinstance(value, list):
        equal = expression.value in value
    else:
        equal = value == expression.value
    return equal if expression.op == "equals" else not equal
