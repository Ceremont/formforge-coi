"""Reusable COI standard sections selected by content, never by filename.

Only source-backed fields and explicitly marked published-policy additions are
produced. No reference JSON or test-set file is read here.
"""

import re
from hashlib import sha256
from .layout_analyzer import fold
from .models import COIExpression, COIHints, DictionaryReference, FieldType, Form, FormField, Section, SourceReference, ValidationRule


def equals(field, value):
    return COIExpression(op="equals", field_id=field.id, value=value)


def any_of(*rules):
    return COIExpression(op="or", rules=list(rules))


def all_of(*rules):
    return COIExpression(op="and", rules=list(rules))


def source_text(document):
    pages = document.analysis.get("page_text", [])
    return "\n".join(p["text"] for p in pages) if pages else "\n".join(b.text for b in document.blocks if b.kind != "blank")


def recipient(text):
    lines = text.splitlines()
    for i, line in enumerate(lines[:45]):
        match = re.search(r"(Wójt\b.*|Burmistrz\b.*|Prezydent\b.*|Starosta\b.*|Urząd\s+(?:Gminy|Miasta|Miejski|Skarbowy)\b.*)", line, re.I)
        if match:
            name = match.group(1).strip()
            if len(name.split()) <= 2 and i + 1 < len(lines) and lines[i + 1].strip():
                name += " " + lines[i + 1].strip()
            return name[:255], not fold(name).startswith("urzad")
    return None, False


def standardize(form, document):
    if form.coi_standardized:
        return form, {"applied": False, "reason": "already_standardized"}
    text = source_text(document)
    normalized = fold(text)
    authority, is_body = recipient(text)
    eligible = bool(authority or re.search(r"wnioskodawca\s*:|dane\s+skladajac|dane\s+wlasciciel", normalized))
    if not eligible:
        return form, {"applied": False, "reason": "No government-applicant context; preserved source structure"}
    raw = list(form.fields)
    fields = []
    sections = []
    used = set()
    suppressed = []
    raw_blocks = [b for b in document.blocks if not b.metadata.get("legal_area")]
    # Spreadsheet empty cells can make a fixed recipient address look like an
    # editable table label. Keep the literal authority header out of residuals.
    header_literals = set()
    in_recipient = False
    for line in text.splitlines()[:70]:
        if re.search(r"wojt\b|burmistrz\b|prezydent\b|starosta\b|urzad\s+(gminy|miasta|miejski|skarbowy)", fold(line)):
            in_recipient = True
        if re.search(r"\bwniosek\b|\bzgloszenie\b|\bdeklaracja\b", fold(line)):
            break
        if in_recipient and line.strip() and not re.search(r"[._…]{3,}", line):
            header_literals.add(fold(line).strip())

    def section(title, tab="Dane", show=None):
        identifier = "s_coi_" + sha256((tab + "/" + title).encode()).hexdigest()[:12]
        result = Section(
            id=identifier, title=title, page=1, order=len(sections), coi=COIHints(origin="standard_policy", policy_rule="COI design standards", tab=tab, show_when=show)
        )
        sections.append(result)
        return result

    def add(sec, label, kind="text", source=None, options=None, required=False, initial=None, default=None, dictionary=None, show=None, rule="COI design standards"):
        identifier = "f_coi_" + sha256((form.id + sec.id + label + str(len(fields))).encode()).hexdigest()[:12]
        ref = source.source_reference.model_copy(deep=True) if source else SourceReference(page=1, block_id="policy:" + slug_rule(rule), text=rule)
        field = FormField(
            id=identifier,
            label=label,
            field_type=FieldType(kind),
            required=required,
            order=len(fields),
            page=sec.page,
            section=sec.id,
            source_reference=ref,
            validation=[ValidationRule(kind=kind)] if kind in ("email", "pesel", "nip", "regon", "postal_code") else [],
            confidence=min(source.confidence, 0.85) if source else 0.65,
            detection_method="source+coi_semantic" if source else "coi_standard_policy",
            options=options or [],
            requires_review=True if not source else source.requires_review,
            help_text=source.help_text if source else "",
            coi=COIHints(
                origin="source" if source else "standard_policy",
                policy_rule=rule,
                tab=sec.coi.tab,
                read_only=bool(initial),
                default_value=initial if initial else default,
                default_value_type="EXTERNAL_SYSTEM" if initial else None,
                dictionary_name=dictionary,
                show_when=show,
            ),
        )
        if dictionary:
            field.dictionary = DictionaryReference(id=dictionary, title=dictionary, source="official", values=options or [])
        if source:
            used.add(source.id)
        fields.append(field)
        return field

    def find(pattern):
        return next((f for f in raw if f.id not in used and re.search(pattern, fold(f.label))), None)

    def evidence(pattern):
        block = next((b for b in raw_blocks if re.search(pattern, fold(b.text))), None)
        if not block:
            return None
        return FormField(
            id="f_evidence_" + sha256(block.id.encode()).hexdigest()[:12],
            label=block.text[:400],
            field_type="text",
            order=0,
            page=block.page,
            section="pending",
            source_reference=SourceReference(
                page=block.page, block_id=block.id, text=block.text, bbox=block.bbox, label_bbox=block.bbox, input_bbox=block.metadata.get("input_bbox")
            ),
            confidence=0.72,
            detection_method="source_context",
            requires_review=True,
        )

    company = bool(re.search(r"\bnip\b|\bregon\b|\bkrs\b|nazwa\s+(firm|wnioskodawc|podmiot)", normalized))
    own_only = bool(re.search(r"wy[łl]acznie we wlasnym imieniu", normalized))
    if authority:
        sec = section("Organ, do którego jest składany wniosek" if is_body else "Urząd, do którego jest składany wniosek")
        org = add(sec, "Nazwa organu" if is_body else "Nazwa urzędu", default=authority)
        org.coi.read_only = True
        org.coi.policy_rule = "Recipient extracted from source header"
    person = None
    role = None
    if not own_only:
        sec = section("Podmiot wniosku")
        person = add(
            sec,
            "Wybierz, w czyim imieniu wnioskujesz",
            "radio",
            options=["Swoim", "Innej osoby"] + (["Osoby prawnej lub jednostki organizacyjnej"] if company else []),
            required=True,
            rule="Design standards pp.9-10; applicant eligibility requires confirmation",
        )
        if company:
            role = add(
                sec,
                "Wybierz, jako kto wnioskujesz",
                "radio",
                options=["Pełnomocnik", "Reprezentant"],
                required=True,
                show=equals(person, "Osoby prawnej lub jednostki organizacyjnej"),
            )
    sec = section("Twoje dane")
    combined = find(r"imie.*nazwisk|nazwisk.*imie")
    for label, kind, initial in [("Imię", "text", "MLPZ.name"), ("Nazwisko", "text", "MLPZ.surname"), ("Numer PESEL", "pesel", "MLPZ.pesel")]:
        src = find(r"\bpesel\b") if kind == "pesel" else combined
        add(sec, label, kind, source=src, required=True, initial=initial, rule="Design standards pp.10-11 + initial data contract")

    def address(title, suffix="", show=None, prefill=False):
        sec = section(title, show=show)
        country = add(sec, "Kraj", "select", options=["Polska"], required=True, default=["Polska"], dictionary="Kraje")
        domestic = equals(country, "Polska")
        foreign = COIExpression(op="not_equals", field_id=country.id, value="Polska")
        for label, kind in [("Miejscowość", "text"), ("Kod pocztowy", "text"), ("Ulica", "text")]:
            add(sec, label, kind, required=True, show=foreign, rule="Foreign address, design standards pp.13-15")
        add(sec, "TERYT_4G_DOWODOWY", "select", required=True, dictionary="TERYT_4G_DOWODOWY", show=domestic, rule="Domestic address cascade from design standards p.14")
        for label, kind, attr in [
            ("Kod pocztowy", "postal_code", "postCode"),
            ("Ulica", "text", "street"),
            ("Numer budynku", "text", "building"),
            ("Numer lokalu", "text", "apartment"),
        ]:
            add(sec, label, kind, required=label != "Numer lokalu", initial="MLPZ." + attr if prefill else None, show=domestic if label in ("Kod pocztowy", "Ulica") else None)
        return sec

    if re.search(r"adres|zamieszkan|siedzib", normalized):
        address("Adres zamieszkania", prefill=True)
    if company and person:
        company_rule = equals(person, "Osoby prawnej lub jednostki organizacyjnej")
        sec = section("Dane podmiotu", show=company_rule)
        for label, kind in [("Nazwa", "text"), ("NIP", "nip"), ("REGON", "regon"), ("Numer KRS", "text")]:
            src = find(r"\bnip\b") if kind == "nip" else find(r"\bregon\b") if kind == "regon" else None
            add(sec, label, kind, source=src, required=label != "Numer KRS", rule="Design standards pp.16-18; confirm company-data scope")
        address("Adres siedziby", show=company_rule)
        representative = all_of(company_rule, equals(role, "Reprezentant"))
        sec = section("Potwierdzenie, że jesteś reprezentantem", show=representative)
        add(sec, "Plik z odpisem danych", "attachment", required=True, rule="Reusable applicant-role block observed in both official examples; confirm legal requirement")
    if person:
        other = equals(person, "Innej osoby")
        sec = section("Dane innej osoby", show=other)
        for label, kind in [("Imię", "text"), ("Nazwisko", "text"), ("Numer PESEL", "pesel")]:
            add(sec, label, kind, required=True, rule="Design standards p.16")
        if re.search(r"adres|zamieszkan", normalized):
            address("Adres zamieszkania innej osoby", show=other)
        authorization = any_of(other, all_of(equals(person, "Osoby prawnej lub jednostki organizacyjnej"), equals(role, "Pełnomocnik"))) if company else other
        sec = section("Pełnomocnictwo", show=authorization)
        add(sec, "Plik dokumentu z pełnomocnictwem", "attachment", required=True, rule="Design standards pp.18-19; confirm attachment restrictions in target system")
        sec = section("Opłata skarbowa", show=other)
        fee = add(
            sec,
            "Czy złożenie pełnomocnictwa wymaga opłaty skarbowej?",
            "radio",
            options=["Tak", "Nie"],
            required=True,
            rule="Design standards pp.19-20; fee applicability requires confirmation",
        )
        add(
            sec, "Informacja o opłacie", "information", show=equals(fee, "Tak")
        ).help_text = "Opłata skarbowa za pełnomocnictwo według dostarczonego standardu: 17 zł. Potwierdź właściwy urząd, rachunek i ewentualne zwolnienie."
        add(sec, "Plik z potwierdzeniem przelewu", "attachment", required=True, show=equals(fee, "Tak"))
        if company:
            sec = section("Opłata skarbowa za pełnomocnictwo", show=all_of(equals(person, "Osoby prawnej lub jednostki organizacyjnej"), equals(role, "Pełnomocnik")))
            add(sec, "Informacja o opłacie", "information").help_text = "Sprawdź należną opłatę i dołącz potwierdzenie przelewu."
            add(sec, "Plik z potwierdzeniem przelewu", "attachment", required=True)
    # Subject fields are inferred from source phrases, not reference filenames.
    subject = "Informacje dotyczące wniosku"
    building = bool(re.search(r"budynk|numeru porzadkowego", normalized))
    refund = bool(re.search(r"nadplat", normalized))
    if building:
        subject = "Informacje o budynku"
    elif refund:
        subject = "Informacje o nadpłacie"
    sec = section("Lokalizacja budynku" if building else subject, subject)

    def subject_field(pattern, label, kind="text", required=True):
        src = find(pattern) or evidence(pattern)
        if src:
            return add(sec, label, kind, source=src, required=required)
        return None

    if building:
        for pattern, label in [(r"miejscowosc", "Miejscowość"), (r"ulic", "Ulica"), (r"ewidencyjn.*dzial", "Numer ewidencyjny działki"), (r"obreb", "Obręb")]:
            subject_field(pattern, label)
    elif refund:
        subject_field(r"rodzaj podatku|nadplat.*tytulu", "Podatek, którego dotyczy nadpłata")
        subject_field(r"kwoci|kwota", "Kwota", "number")
        subject_field(r"uzasadn", "Uzasadnienie", "textarea")
        if "zaliczyc" in normalized and "zwrocic" in normalized:
            sec = section("Rozliczenie nadpłaty", subject)
            choice = add(
                sec,
                "Wybierz, co mamy zrobić z nadpłatą",
                "radio",
                source=evidence(r"kwot.*nadplat.*prosze"),
                options=["Zaliczyć na poczet przyszłego zobowiązania podatkowego", "Zwrócić przelewem na rachunek bankowy"],
                required=True,
                rule="Mutually exclusive ordinal repayment alternatives in source",
            )
            add(sec, "Nazwa podatku", source=evidence(r"zaliczyc.*tytulu"), required=True, show=equals(choice, choice.options[0]))
            add(sec, "Numer rachunku", source=evidence(r"rachunek"), required=True, show=equals(choice, choice.options[1]))
        if re.search(r"korekta deklaracji", normalized):
            sec = section("Korekta deklaracji", subject)
            add(sec, "Plik deklaracji podatkowej", "attachment", source=find(r"korekta deklaracji") or evidence(r"korekta deklaracji"), required=True)
    # Retain unclassified meaningful source fields; paper date/signature/privacy
    # are documented exclusions under the electronic-workflow standard.
    residual = []
    for field in raw:
        label = fold(field.label).strip(" ()*:")
        if field.id in used:
            continue
        if label in header_literals or label == fold(form.title) or fold(form.title).endswith(" " + label):
            suppressed.append({"id": field.id, "label": field.label, "reason": "fixed recipient header or form title"})
            continue
        if re.search(
            r"podpis|^data$|dnia|wnioskodawc|adresat|imie|nazwisk|pesel|nip|regon|^adres|telefon|e.?mail|w zalaczeniu|kwot.*nadplat.*prosze|zaliczyc.*zobowiaz|zwrocic.*rachunek",
            label,
        ):
            suppressed.append({"id": field.id, "label": field.label, "reason": "replaced by standard section or electronic workflow"})
            continue
        if building and re.search(r"miejscowosc|ulic|ewidencyjn|obreb|wnosze", label):
            continue
        if refund and re.search(r"nadplat.*tytulu|kwoci|rodzaj podatku|uzasadn|zaliczyc|zwr", label):
            continue
        if len(label) < 3 or len(label) > 110 or "@" in label or re.search(r"przetwarz|administrator|inspektor|praw|zgodnie|panstwa|kontaktowac", label):
            continue
        residual.append(field)
    if residual:
        sec = section("Pozostałe dane źródłowe", subject)
        for field in residual:
            add(sec, field.label, field.field_type, source=field, options=field.options, required=field.required)
    sec = section("Dane do kontaktu", "Kontakt i zgody")
    for label, kind, pattern, initial in [("Numer telefonu", "phone", r"telefon", "MLPZ.phoneNumber"), ("Adres e-mail", "email", r"e.?mail", "MLPZ.email")]:
        add(sec, label, kind, source=find(pattern), initial=initial, rule="Design standards pp.24-25; external data are readOnly under initial-data contract")
    if eligible:
        sec = section("Zgoda", "Kontakt i zgody")
        consent = add(sec, "Zgoda", "consent", required=False, rule="Design standards pp.25-27; consent wording, requiredness and link require confirmation")
        consent.help_text = "Potwierdzam zapoznanie się z klauzulą informacyjną. Przed publikacją dodaj właściwy odnośnik do pełnej treści klauzuli."
    populated = {f.section for f in fields}
    sections = [s for s in sections if s.id in populated]
    result = Form(
        id=form.id,
        title=form.title,
        pages=form.pages,
        sections=sections,
        fields=fields,
        warnings=form.warnings + ["Sekcje dodane na podstawie standardu COI wymagają potwierdzenia uprawnień, opłat i treści zgód. Nie pobierano danych z rejestrów."],
        coi_standardized=True,
    )
    return result, {
        "applied": True,
        "source_fields": len(raw),
        "output_fields": len(fields),
        "standard_additions": sum(f.coi.origin == "standard_policy" for f in fields),
        "suppressed": suppressed,
        "policy": "published design standards; content-driven applicant profile",
        "reference_json_used_at_runtime": False,
    }


def slug_rule(text):
    return re.sub(r"[^a-z0-9]+", "_", fold(text))[:90]
