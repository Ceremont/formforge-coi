"""Reporting counts and filled blankette guards; COI serialization is unchanged."""
import copy
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from formforge.coi_mapper import export_bundle
from formforge.coi_validation import fields_with_context
from formforge.config import Settings
from formforge.models import COIExpression, DictionaryReference, FieldGroup, Form
from formforge.pipeline import convert
from formforge.quality_review import review


def test_counts_include_source_policy_manual_and_nested_states(sample_form):
    form = sample_form.model_copy(deep=True)
    first, second, third = form.fields[:3]
    first.field_type = 'radio'
    first.options = ['Tak', 'Nie']
    second.conditions = []
    second.coi.origin = 'source'
    second.coi.show_when = COIExpression(op='equals', field_id=first.id, value='Tak')
    third.conditions = []
    third.coi.origin = 'standard_policy'
    third.coi.read_only_when = COIExpression(op='equals', field_id=first.id, value='Nie')
    section = form.sections[0]
    section.coi.origin = 'manual'
    # A container state affects every child; it must not be omitted in exported totals.
    controller = next(f for f in form.fields if f.section != section.id)
    controller.field_type = 'radio'
    controller.options = ['Tak', 'Nie']
    section.coi.show_when = COIExpression(op='equals', field_id=controller.id, value='Tak')
    form.groups.append(FieldGroup(id='group_ux', title='Powtarzanie', section=second.section, repeat_key='repeat_ux'))
    second.group_id = 'group_ux'
    form.dictionaries.append(DictionaryReference(id='unused_ux', source='proposed', values=['A'], title='Unused catalog definition'))
    export, coi = export_bundle(form)
    before = copy.deepcopy(export)
    report = review(form, [], coi, export)
    m = report['metrics']
    assert m['dependencies']['source'] >= 1
    assert m['dependencies']['standard_policy'] >= 1
    assert m['dependencies']['manual'] >= 1
    real = sum(len(f['states']) for _, _, f, _ in fields_with_context(export))
    assert m['dependencies']['exported_states'] == real
    assert m['dependencies']['exported_by_type']['SHOW'] >= 2
    assert m['dependencies']['exported_by_type']['READ_ONLY'] >= 1
    assert m['model']['dictionaries_used'] < m['model']['dictionary_definitions']
    assert m['export']['pages'] == len(export['tabs'])
    assert m['export']['components_total'] == len(list(fields_with_context(export)))
    assert export == before, 'Reporting must never mutate the COI export'


def test_missing_export_is_not_a_false_zero(sample_form):
    result = review(sample_form, [], {})
    assert result['metrics']['dependencies']['exported_states'] is None
    assert not result['metrics']['export']['available']


def test_confirmed_policy_field_is_not_still_counted_as_unconfirmed(sample_form):
    item = sample_form.fields[0]
    item.coi.origin = 'standard_policy'
    item.requires_review = True
    item.confidence = .5
    first = review(sample_form, [], {})['counts']['review_fields']
    item.coi.confirmed = True
    assert review(sample_form, [], {})['counts']['review_fields'] == first - 1


def test_filled_acroform_values_never_become_labels_or_defaults(tmp_path):
    pdfmetrics.registerFont(TTFont('UXDejaVu', str(Path(__file__).resolve().parents[1] / 'docs/assets/fonts/DejaVuSans.ttf')))
    path = tmp_path / 'filled-fictional.pdf'
    pdf = Canvas(str(path))
    pdf.setFont('UXDejaVu', 12)
    pdf.drawString(50, 790, 'URZĄD PRZYKŁADOWY — WNIOSEK')
    pdf.drawString(50, 740, 'Imię i nazwisko')
    pdf.acroForm.textfield(name='applicant_name', tooltip='Imię i nazwisko', x=50, y=700, width=300, height=25, value='Jan Fikcyjny UX')
    pdf.drawString(50, 650, 'Adres e-mail')
    pdf.acroForm.textfield(name='email', tooltip='Adres e-mail', x=50, y=610, width=300, height=25, value='fikcyjny.ux@example.invalid')
    pdf.showPage()
    pdf.save()
    result = convert(path, 'unknown.pdf', 'pdf', Settings())
    form = Form.model_validate(result['form'])
    assert any('URZĄD PRZYKŁADOWY' in b['text'] for b in result['document']['blocks'])
    assert any(f.label == 'Imię i nazwisko' for f in form.fields)
    assert any(f.field_type == 'email' for f in form.fields)
    for f in form.fields:
        assert 'Jan Fikcyjny UX' not in f.label and 'fikcyjny.ux@example.invalid' not in f.label
        assert f.coi.default_value not in ['Jan Fikcyjny UX', 'fikcyjny.ux@example.invalid']
    assert 'Jan Fikcyjny UX' not in str(form.initial_data)
    assert 'fikcyjny.ux@example.invalid' not in str(form.initial_data)
    for _, _, component, _ in fields_with_context(result['export']):
        assert component.get('defaultValue') not in ['Jan Fikcyjny UX', 'fikcyjny.ux@example.invalid']


def test_filled_docx_answers_are_not_labels_or_initial_values(tmp_path):
    from docx import Document
    doc = Document()
    doc.add_heading('URZĄD PRZYKŁADOWY — WNIOSEK', 0)
    table = doc.add_table(rows=3, cols=2)
    for cells, values in zip(table.rows, [('Imię i nazwisko:', 'Jan Fikcyjny UX'), ('Adres e-mail:', 'fikcyjny.ux@example.invalid'), ('Telefon:', '555111222')], strict=True):
        cells.cells[0].text, cells.cells[1].text = values
    source = tmp_path / 'filled-fictional.docx'
    doc.save(source)
    result = convert(source, 'unseen.docx', 'docx', Settings())
    assert any('URZĄD PRZYKŁADOWY' in b['text'] for b in result['document']['blocks'])
    answers = ['Jan Fikcyjny UX', 'fikcyjny.ux@example.invalid', '555111222']
    for item in result['form']['fields']:
        assert not any(answer in item['label'] for answer in answers)
        assert item['coi']['default_value'] not in answers
    assert not any(answer in str(result['form']['initial_data']) for answer in answers)


def test_source_field_with_policy_condition_counts_as_policy(sample_form):
    from formforge.quality_review import metrics
    f, parent = sample_form.fields[:2]
    f.coi.origin = 'source'
    f.coi.policy_rule = 'COI design standards'
    f.coi.show_when = COIExpression(op='equals', field_id=parent.id, value='Tak')
    counts = metrics(sample_form)['dependencies']
    assert counts['standard_policy'] == 1
    assert counts['source'] == 0


def test_manual_rule_and_missing_legacy_evidence_are_separate(sample_form):
    from formforge.models import ConditionalRule
    from formforge.quality_review import metrics
    f, parent = sample_form.fields[:2]
    f.conditions = [ConditionalRule(field_id=parent.id, value='A', evidence='Reguła dodana ręcznie przez użytkownika'), ConditionalRule(field_id=parent.id, value='B')]
    counts = metrics(sample_form)['dependencies']
    assert counts['manual'] == 1
    assert counts['unverified'] == 1
    assert counts['source'] == 0
