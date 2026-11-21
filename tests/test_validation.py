import pytest

from formforge.form_validator import FormValidator, valid_pesel
from formforge.models import ConditionalRule, FieldType, ValidationRule


@pytest.mark.parametrize("value,expected", [("44051401458", True), ("02070803628", True), ("44051401459", False), ("00000000000", False), ("abcdefghijk", False), ("123", False)])
def test_pesel(value, expected):
    assert valid_pesel(value) is expected


@pytest.mark.parametrize(
    "kind,value,valid",
    [
        ("email", "a@b.pl", True),
        ("email", "a@", False),
        ("phone", "+48 123 456 789", True),
        ("phone", "hello", False),
        ("postal_code", "00-123", True),
        ("postal_code", "00123", False),
        ("date", "2024-02-29", True),
        ("date", "2026-02-29", False),
        ("number", "12.5", True),
        ("number", "NaN", False),
        ("number", True, False),
        ("checkbox", True, True),
        ("checkbox", "yes", False),
    ],
)
def test_value_rules(sample_form, kind, value, valid):
    field = sample_form.fields[0].model_copy(update={"field_type": FieldType(kind), "validation": [], "required": False})
    assert (FormValidator()._value_error(field, value) is None) == valid


def test_required_and_hidden_values(sample_form):
    first, second = sample_form.fields[:2]
    first.field_type = FieldType.CHECKBOX
    first.required = False
    first.validation = []
    second.conditions = [ConditionalRule(field_id=first.id, value=True)]
    second.required = True
    for field in sample_form.fields[2:]:
        field.required = False
        field.validation = []
    assert not FormValidator().values(sample_form, {first.id: False})
    assert any(i.field_id == second.id and i.code == "required" for i in FormValidator().values(sample_form, {first.id: True}))


def test_length_and_number_bounds(sample_form):
    field = sample_form.fields[0]
    field.field_type = FieldType.TEXT
    field.validation = [ValidationRule(kind="max_length", value=3)]
    assert FormValidator()._value_error(field, "abcd")
    field.field_type = FieldType.NUMBER
    field.validation = [ValidationRule(kind="min", value=2), ValidationRule(kind="max", value=8)]
    assert FormValidator()._value_error(field, 1)
    assert FormValidator()._value_error(field, 9)
    assert FormValidator()._value_error(field, 4) is None
