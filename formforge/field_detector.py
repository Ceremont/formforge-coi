import re
from hashlib import sha256

from .layout_analyzer import fold
from .models import Block, DictionaryReference, ExtractedDocument, FieldType, FormField, SourceReference, ValidationRule


CHOICE = re.compile(r"(?:\[\s*[xX]?\s*\]|[☐□☑○◯❑\uf0f0\uf092]|\(\s*\))\s*([^\[☐□☑○◯❑\uf0f0\uf092]+?)(?=(?:\[\s*[xX]?\s*\]|[☐□☑○◯❑\uf0f0\uf092]|\(\s*\))|$)")
MARKER = re.compile(r"[.·…]{3,}|_{3,}|…|\[\s*\]")
TYPE_RULES = [
    (r"\bpesel\b", FieldType.PESEL),
    (r"\bnip\b", FieldType.NIP),
    (r"\bregon\b", FieldType.REGON),
    (r"\b(e-?mail|poczt[ay] elektroniczn[ae]j?)\b", FieldType.EMAIL),
    (r"\b(telefon(?:u|iczny|icznego)?|tel\.?|phone)\b", FieldType.PHONE),
    (r"\b(kod pocztowy|postal code)\b", FieldType.POSTAL_CODE),
    (r"\b(data|date|termin(?:ie|u)?)\b|(?:od|do) dnia|(?:rrrr|yyyy)[-/.](?:mm)[-/.](?:dd)|(?:dd)[-/.](?:mm)[-/.](?:rrrr|yyyy)", FieldType.DATE),
    (r"\b(liczba|ilosc|kwota|wysokosc oplaty|powierzchnia|dlugosc|szerokosc|obwod|razem|number|amount)\b|^nr$", FieldType.NUMBER),
    (r"\b(uzasadnienie|opis|uwagi|description|przyczyna)\b|z powodu|nastepujacym zakresie", FieldType.TEXTAREA),
    (r"\b(zalacznik|zalaczniki|attachment)\b", FieldType.ATTACHMENT),
    (r"\b(adres|address)\b", FieldType.ADDRESS),
]


class FieldDetector:
    def detect(self, document: ExtractedDocument) -> list[FormField]:
        fields = []
        for block in document.blocks:
            if block.kind in ("heading", "blank", "instruction", "legal", "information", "table") or block.metadata.get("formula"):
                continue
            text = block.text.strip()
            if len(text) > 1500:
                continue
            candidates = self._candidates(block)
            for label, kind, options, confidence in candidates:
                label = re.sub(r"^\s*\d+[.)]\s*", "", label)
                label = MARKER.sub("", label).strip(" .…:_;-*\t\n")
                if not label or len(label) > 400 or len(re.sub(r"[^\w]", "", label)) < 2 or not any(c.isalpha() for c in label):
                    continue

                # Native fields supersede matching printed labels on the same page.
                def same_region(field):
                    ref = field.source_reference
                    if ref.block_id == block.id:
                        return True
                    if ref.cell and block.metadata.get("cell"):
                        return ref.cell == block.metadata["cell"] and ref.sheet == block.metadata.get("sheet")
                    a, b = ref.input_bbox or ref.bbox, block.metadata.get("input_bbox") or block.bbox
                    if ref.label_bbox and block.bbox:
                        x, y = ref.label_bbox, block.bbox
                        overlap = max(0, min(x[2], y[2]) - max(x[0], y[0])) * max(0, min(x[3], y[3]) - max(x[1], y[1]))
                        if overlap > 0.5 * max(1, min((x[2] - x[0]) * (x[3] - x[1]), (y[2] - y[0]) * (y[3] - y[1]))):
                            return True
                    if a and b:
                        overlap = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
                        return overlap > 0.2 * max(1, min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])))
                    return False

                existing = next((f for f in fields if f.page == block.page and fold(f.label) == fold(label) and same_region(f)), None)
                if existing and block.kind != "form_field":
                    continue
                if existing:
                    fields.remove(existing)
                normalized = re.sub(r"(?<=[a-z])\d{1,2}\b", "", fold(label))
                if kind == FieldType.TEXT:
                    kind = next((field_type for pattern, field_type in TYPE_RULES if re.search(pattern, normalized)), FieldType.TEXT)
                    simple_text = re.search(r"imie|nazwisk|miejscowosc|ulica|nr domu|nr lokalu|numer (?:domu|lokalu|rachunku)|rasa psa", normalized)
                    if kind == FieldType.TEXT and block.metadata.get("multiline") and not simple_text:
                        kind = FieldType.TEXTAREA
                if label.lower() == "do" and fields and fields[-1].field_type == FieldType.DATE:
                    kind = FieldType.DATE
                    label = "do (koniec terminu)"
                alternative_contact = "/" in label and "adres" in normalized and "mail" in normalized and "telefon" in normalized
                if alternative_contact:
                    kind = FieldType.TEXT
                required = bool(block.metadata.get("required")) or bool(re.search(r"\*|\bobowiazkow[eya]\b|\bwymagan[eya]\b", fold(text)))
                if re.search(r"opcjonaln|nie (?:są|sa) (?:obowiązkowe|obowiazkowe)|nieobowiazk", fold(text)):
                    required = False
                validation = self._rules(kind, text)
                field_id = "f_" + sha256(f"{block.page}:{block.id}:{label}".encode()).hexdigest()[:12]
                review = (
                    min(confidence, block.confidence) < 0.8
                    or normalized != fold(label)
                    or alternative_contact
                    or bool(block.metadata.get("requires_review"))
                    or bool(re.search(r"\b(jezeli|jesli|w przypadku|o ile|when|if)\b", fold(text)))
                )
                fields.append(
                    FormField(
                        id=field_id,
                        label=label,
                        field_type=kind,
                        required=required,
                        order=len(fields),
                        page=block.page,
                        section="pending",
                        validation=validation,
                        source_reference=SourceReference(
                            page=block.page,
                            block_id=block.id,
                            text=block.metadata.get("source_text", text),
                            bbox=block.bbox,
                            sheet=block.metadata.get("sheet"),
                            cell=block.metadata.get("cell"),
                            input_bbox=block.metadata.get("input_bbox"),
                            label_bbox=block.bbox,
                        ),
                        confidence=round(min(confidence, block.confidence), 3),
                        detection_method=block.method + "+rules",
                        decision_reasons=[
                            r
                            for r in [
                                block.metadata.get("choice_evidence"),
                                "Explicit answer marker"
                                if MARKER.search(text)
                                else "Native form control"
                                if block.kind == "form_field"
                                else "Spatial label/answer association"
                                if block.metadata.get("label_input_pair")
                                else "Label/type context",
                                f"Semantic type: {kind.value}",
                            ]
                            if r
                        ],
                        options=options,
                        dictionary=DictionaryReference(id=f"dict_{field_id}", source="document", values=options) if options else None,
                        requires_review=review,
                        help_text="Wymagane zgodnie z oznaczeniem w dokumencie." if required else "",
                    )
                )
        from .models import ConditionalRule

        source_map = {f.source_reference.block_id: f for f in fields}
        for field in fields:
            block = next(b for b in document.blocks if b.id == field.source_reference.block_id)
            parent = source_map.get(block.metadata.get("show_if_block"))
            if parent:
                field.conditions.append(
                    ConditionalRule(field_id=parent.id, value=block.metadata["show_if_value"], evidence=block.metadata.get("source_text", block.text), requires_review=True)
                )
                field.requires_review = True
        return fields

    def _candidates(self, block: Block):
        text = block.text
        if block.kind == "form_field":
            return [(text, FieldType(block.metadata.get("native_type", "text")), block.metadata.get("options", []), 0.98 if "candidate" not in block.method else 0.55)]
        if block.metadata.get("label_input_pair") and not MARKER.search(text) and not CHOICE.search(text):
            return [(text, FieldType.TEXT, [], 0.84)]
        choices = [m.group(1).strip(" ;:.") for m in CHOICE.finditer(text)]
        if choices:
            first = CHOICE.search(text)
            prefix = text[: first.start()].strip(" :")
            if len(choices) > 1:
                if not prefix:
                    # No invented group title: retain independent choices for review.
                    return [(choice, FieldType.CHECKBOX, [], 0.68) for choice in choices]
                kind = FieldType.RADIO if re.search(r"[○◯]|\(\s*\)|jedn[ao]|tak.*nie", fold(text)) else FieldType.SELECT if "wybierz" in fold(prefix) else FieldType.RADIO
                return [(prefix, kind, choices, 0.86)]
            return [((prefix + " " + choices[0]).strip(), FieldType.CHECKBOX, [], 0.86)]
        if re.match(r"^(?:Uwaga|Instrukcja|Pouczenie|Podstawa prawna|Prosimy|Należy|Wypełnij)\b", text, re.I):
            return []
        if "wybierz" in fold(text) and ":" in text:
            label, options_text = text.split(":", 1)
            options = [s.strip() for s in re.split(r"[;|]", options_text) if s.strip()]
            if len(options) > 1:
                return [(label, FieldType.SELECT, options, 0.88)]
        # Multiple labelled blank spaces on one physical line.
        if MARKER.search(text):
            parts = MARKER.split(text)
            labels = [p.strip(" .…:_;-\n") for p in parts[:-1] if p.strip(" .…:_;-\n")]
            if labels:
                return [(label, FieldType.TEXT, [], 0.9) for label in labels]
            caption = parts[-1].strip()
            if caption.startswith("(") and caption.endswith(")") and len(caption) < 120 and re.search(r"\b(imie|nazwisko|adres|telefon|telefonu|pesel|nip|regon|kod pocztowy)\b", fold(caption)):
                return [(caption.strip("() "), FieldType.TEXT, [], 0.85)]
        if ":" in text:
            label, tail = text.split(":", 1)
            if len(label) < 140 and not re.search(r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]", tail) and len(label.split()) <= 18:
                return [(label, FieldType.TEXT, [], 0.85)]
        if block.metadata.get("paired_blank") and len(text) < 140:
            return [(text, FieldType.TEXT, [], 0.77)]
        if block.method == "tesseract_ocr" and len(text.split()) <= 5 and any(re.search(pattern, fold(text)) for pattern, _ in TYPE_RULES):
            return [(text, FieldType.TEXT, [], 0.68)]
        return []

    def _rules(self, kind, text):
        rules = []
        if kind in (FieldType.EMAIL, FieldType.PESEL, FieldType.NIP, FieldType.REGON, FieldType.PHONE, FieldType.POSTAL_CODE, FieldType.DATE):
            rules.append(ValidationRule(kind=kind.value))
        if kind == FieldType.PESEL:
            rules.extend([ValidationRule(kind="min_length", value=11), ValidationRule(kind="max_length", value=11)])
        for pattern, rule_kind in [(r"(?:maks\.?|max\.?|maksymalnie)\s*(\d+)\s*znak", "max_length"), (r"(?:min\.?|minimum)\s*(\d+)\s*znak", "min_length")]:
            match = re.search(pattern, fold(text))
            if match:
                rules.append(ValidationRule(kind=rule_kind, value=int(match.group(1))))
        return rules
