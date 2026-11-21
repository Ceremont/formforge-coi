from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field as PydanticField, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_max_length=20_000, allow_inf_nan=False)


class FieldType(StrEnum):
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    DATE = "date"
    EMAIL = "email"
    PHONE = "phone"
    PESEL = "pesel"
    NIP = "nip"
    REGON = "regon"
    POSTAL_CODE = "postal_code"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    SELECT = "select"
    ADDRESS = "address"
    ATTACHMENT = "attachment"
    INFORMATION = "information"
    CONSENT = "consent"


class SourceReference(Model):
    page: int = PydanticField(ge=1)
    block_id: str
    text: str
    bbox: tuple[float, float, float, float] | None = None
    sheet: str | None = None
    cell: str | None = None
    input_bbox: tuple[float, float, float, float] | None = None
    label_bbox: tuple[float, float, float, float] | None = None


class Block(Model):
    id: str
    text: str
    page: int = PydanticField(ge=1)
    kind: Literal["text", "heading", "cell", "form_field", "list", "blank", "instruction", "legal", "information", "option", "table"] = "text"
    bbox: tuple[float, float, float, float] | None = None
    metadata: dict[str, Any] = PydanticField(default_factory=dict)
    method: str = "text"
    confidence: float = PydanticField(default=1, ge=0, le=1)


class Page(Model):
    id: int = PydanticField(ge=1)
    title: str
    width: float | None = None
    height: float | None = None
    source: str = "document"


class ExtractedDocument(Model):
    filename: str
    format: str
    pages: list[Page]
    blocks: list[Block]
    warnings: list[str] = PydanticField(default_factory=list)
    analysis: dict[str, Any] = PydanticField(default_factory=dict)


class ValidationRule(Model):
    kind: Literal["required", "min_length", "max_length", "min", "max", "email", "pesel", "nip", "regon", "phone", "postal_code", "date"]
    value: int | float | str | None = None
    message: str | None = None

    @model_validator(mode="after")
    def validate_bound(self):
        if self.kind in ("min_length", "max_length"):
            if not isinstance(self.value, int) or isinstance(self.value, bool) or not 0 <= self.value <= 1_000_000:
                raise ValueError("Ograniczenie długości musi być liczbą całkowitą od 0 do 1000000")
        if self.kind in ("min", "max") and (not isinstance(self.value, (int, float)) or isinstance(self.value, bool)):
            raise ValueError("Ograniczenie wartości musi być liczbą")
        return self


class ConditionalRule(Model):
    field_id: str
    operator: Literal["equals", "not_equals"] = "equals"
    value: str | bool
    action: Literal["show", "require"] = "show"


class DictionaryReference(Model):
    id: str
    source: Literal["document", "official", "proposed"]
    values: list[str] = PydanticField(default_factory=list, max_length=500)
    title: str = ""
    aliases: list[str] = PydanticField(default_factory=list, max_length=100)


class COIExpression(Model):
    op: Literal["equals", "not_equals", "and", "or"]
    field_id: str | None = None
    value: str | bool | None = None
    rules: list["COIExpression"] = PydanticField(default_factory=list, max_length=20)

    def references(self, depth=0):
        if depth > 16:
            raise ValueError("Zbyt głębokie wyrażenie COI")
        if self.op in ("equals", "not_equals"):
            if not self.field_id or self.value is None or self.rules:
                raise ValueError("Nieprawidłowy warunek COI")
            return {self.field_id}
        if not self.rules or self.field_id:
            raise ValueError("Pusta grupa warunków COI")
        return set().union(*(r.references(depth + 1) for r in self.rules))


class COIHints(Model):
    origin: Literal["source", "standard_policy", "manual"] = "source"
    policy_rule: str = ""
    tab: str = ""
    read_only: bool = False
    default_value: str | list[str] | int | float | bool | None = None
    default_value_type: Literal["EXTERNAL_SYSTEM"] | None = None
    dictionary_name: str | None = None
    show_when: COIExpression | None = None
    read_only_when: COIExpression | None = None
    consent_required: bool = False
    confirmed: bool = False


class FormField(Model):
    id: str = PydanticField(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,100}$")
    label: str = PydanticField(min_length=1, max_length=2000)
    field_type: FieldType
    required: bool = False
    order: int = PydanticField(ge=0)
    page: int = PydanticField(ge=1)
    section: str
    validation: list[ValidationRule] = PydanticField(default_factory=list, max_length=30)
    source_reference: SourceReference
    confidence: float = PydanticField(ge=0, le=1)
    detection_method: str
    options: list[str] = PydanticField(default_factory=list, max_length=500)
    conditions: list[ConditionalRule] = PydanticField(default_factory=list, max_length=10)
    dictionary: DictionaryReference | None = None
    requires_review: bool = False
    help_text: str = ""
    group_id: str | None = None
    required_conditions: list[ConditionalRule] = PydanticField(default_factory=list, max_length=10)
    coi: COIHints = PydanticField(default_factory=COIHints)


class Section(Model):
    id: str
    title: str
    page: int = PydanticField(ge=1)
    order: int = PydanticField(ge=0)
    instructions: list[str] = PydanticField(default_factory=list)
    conditions: list[ConditionalRule] = PydanticField(default_factory=list, max_length=10)
    coi: COIHints = PydanticField(default_factory=COIHints)


class FieldGroup(Model):
    id: str
    title: str
    section: str
    parent_id: str | None = None
    repeat_key: str | None = None


class Form(Model):
    schema_version: Literal["formforge/1.0"] = "formforge/1.0"
    id: str
    title: str = PydanticField(min_length=1)
    language: str = "pl"
    pages: list[Page] = PydanticField(min_length=1, max_length=100)
    sections: list[Section] = PydanticField(min_length=1, max_length=2000)
    fields: list[FormField] = PydanticField(default_factory=list, max_length=5000)
    warnings: list[str] = PydanticField(default_factory=list)
    groups: list[FieldGroup] = PydanticField(default_factory=list, max_length=1000)
    dictionaries: list[DictionaryReference] = PydanticField(default_factory=list, max_length=1000)
    initial_data: dict[str, str | bool | int | float] = PydanticField(default_factory=dict)
    confidence_semantics: Literal["heuristic_score_not_calibrated_probability"] = "heuristic_score_not_calibrated_probability"
    coi_standardized: bool = False

    @model_validator(mode="after")
    def check_references(self):
        page_ids = {p.id for p in self.pages}
        section_ids = {s.id for s in self.sections}
        field_ids = {f.id for f in self.fields}
        if len(page_ids) != len(self.pages) or len(section_ids) != len(self.sections) or len(field_ids) != len(self.fields):
            raise ValueError("Identyfikatory muszą być unikalne")
        section_pages = {s.id: s.page for s in self.sections}
        groups = {g.id: g for g in self.groups}
        if len(groups) != len(self.groups) or len({d.id for d in self.dictionaries}) != len(self.dictionaries):
            raise ValueError("Grupy i słowniki muszą mieć unikalne identyfikatory")
        if self.initial_data.keys() - field_ids:
            raise ValueError("Dane inicjalne odwołują się do nieznanych pól")
        for group in self.groups:
            if group.section not in section_ids:
                raise ValueError("Nieznana sekcja grupy")
            seen, current = set(), group
            while current.parent_id:
                if current.id in seen or current.parent_id not in groups or len(seen) > 16:
                    raise ValueError("Nieprawidłowa lub cykliczna hierarchia grup")
                seen.add(current.id)
                current = groups[current.parent_id]
                if current.section != group.section:
                    raise ValueError("Grupy nadrzędne muszą należeć do tej samej sekcji")
        for section in self.sections:
            if section.page not in page_ids:
                raise ValueError("Sekcja odwołuje się do nieistniejącej strony")
        for field in self.fields:
            if field.group_id and (field.group_id not in groups or groups[field.group_id].section != field.section):
                raise ValueError("Pole odwołuje się do nieprawidłowej grupy")
            if field.page not in page_ids or field.section not in section_ids:
                raise ValueError("Pole odwołuje się do nieistniejącej strony lub sekcji")
            if section_pages[field.section] != field.page:
                raise ValueError("Strona pola i sekcji muszą być zgodne")
            if field.source_reference.page not in page_ids:
                raise ValueError("Nieprawidłowe odwołanie do źródła")
            if any(c.field_id not in field_ids or c.field_id == field.id for c in field.conditions + field.required_conditions):
                raise ValueError("Nieprawidłowe odwołanie w warunku widoczności")
        section_conditions = {s.id: s.conditions for s in self.sections}
        if any(c.field_id not in field_ids for s in self.sections for c in s.conditions):
            raise ValueError("Sekcja ma warunek odwołujący się do nieznanego pola")
        section_map = {s.id: s for s in self.sections}
        graph = {f.id: [c.field_id for c in f.conditions + f.required_conditions + section_conditions[f.section]] for f in self.fields}
        for field in self.fields:
            expressions = [field.coi.show_when, field.coi.read_only_when, section_map[field.section].coi.show_when]
            for expression in expressions:
                if expression:
                    refs = expression.references()
                    if refs - field_ids:
                        raise ValueError("Nieznane pole w wyrażeniu COI")
                    graph[field.id].extend(refs)
        active, depths = set(), {}

        def visit(node):
            if len(active) > 32:
                raise ValueError("Zbyt wiele zagnieżdżonych warunków")
            if node in active:
                raise ValueError("Cykliczne warunki widoczności")
            if node in depths:
                return depths[node]
            active.add(node)
            depth = 1 + max((visit(parent) for parent in graph[node]), default=0)
            active.remove(node)
            if depth > 32:
                raise ValueError("Zbyt wiele zagnieżdżonych warunków")
            depths[node] = depth
            return depth

        for node in graph:
            visit(node)
        return self


class Issue(Model):
    severity: Literal["error", "warning", "info"]
    code: str
    message: str
    field_id: str | None = None


class ValidateRequest(Model):
    form: Form
    values: dict[str, Any] | None = None
    export_format: Literal["official", "preview"] = "official"


class PreviewRequest(Model):
    form: Form
    export_format: Literal["official", "preview"] = "official"
