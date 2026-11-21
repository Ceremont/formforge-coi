"""Conservative role/choice interpretation using source evidence and geometry."""

import re
from collections import Counter
from .layout_analyzer import fold
from .models import Block

BOX = r"(?:\[\s*[xX]?\s*\]|[□☐☑○◯❑\uf0f0\uf092])"
START = re.compile(r"^\s*" + BOX + r"\s*(.+)")
BLANK = re.compile(r"[._…·]{3,}")
SECTION = re.compile(
    r"^(?:[a-z](?:\.\d+)*|\d+(?:\.\d+)*)[.)]?\s+(?:dane|informacje|instrukcja|adres|zalaczniki|oswiadczeni|okolicznosci|obliczeni|podpis|data i podpis|wnioskodawca)"
)


def understand(document):
    from .field_detector import CHOICE

    output = []
    legal = False
    attachments = False
    for block in document.blocks:
        text = block.text.strip()
        normalized = " ".join(fold(text).split())
        clean = re.sub(r"^(?:[ivx]+[.)]|\d+(?:\.\d+)*[.)]?)\s*", "", normalized)
        start_legal = bool(
            re.match(r"(?:klauzula informacyjna|informacj[ae].*przetwarzani|obowiazek informacyjny|administratorem (?:pana|pani|danych)|zgodnie z art\.?\s*13)", clean)
        )
        if start_legal:
            legal = True
        elif re.match(r"(?:wniosek|deklaracja|formularz|zgloszenie|zgody|zgoda kandydata|dane sportowca|dane trenera)\b", clean):
            legal = False
        if legal:
            block.kind = "legal"
            block.metadata["legal_area"] = True
        elif block.metadata.get("legal_area"):
            block.metadata.pop("legal_area", None)
            block.kind = "text"
        if legal:
            output.append(block)
            continue
        reason = None
        if block.method == "tesseract_ocr" and block.confidence < 0.3 and not re.search(r"\bpesel\b|\bnip\b|\bregon\b", normalized):
            block.kind = "information"
            reason = "Unreadable low-confidence OCR label retained for inspection, not promoted to input"
        elif re.fullmatch(r"(?:strona\s+)?\d{1,2}\s*/\s*\d{1,2}", normalized):
            block.kind = "information"
            reason = "page number"
        elif re.search(r"\b(?:podpis|pieczec)\b", normalized) and not re.search(r"podpisan|plik|dokument", normalized):
            block.kind = "information"
            reason = "paper signature or stamp, not citizen input"
        elif re.search(r"miejscowosc i data|^[^:]{0,50},\s*dni(?:a)?\b|^dnia\b", normalized):
            block.kind = "information"
            reason = "paper place/date header; electronic completion uses finish page"
        elif re.match(r"(?:uwaga|instrukcja|pouczenie|wypelnij|wypelniaj|nalezy|niepotrzebne skreslic|postaw|zaznacz|wypelnia organ)\b", clean):
            block.kind = "instruction"
            reason = "explicit completion instruction"
        elif SECTION.match(normalized) and not BLANK.search(text):
            block.kind = "heading"
            reason = "numbered thematic section"
        elif re.match(
            r"(?:dane (?:kandydat|sportowca|trenera)|rodzaje wnioskow|informacja o posiadanym|zalacznikow z tabel|zalaczyc do wniosku|ale ulatwia kontakt)", normalized
        ) and not BLANK.search(text):
            block.kind = "heading" if normalized.startswith(("dane", "rodzaje", "informacja")) else "instruction"
            reason = "source section or continuation of guidance"
        elif re.match(r"art\.\s*\d|^numer konta:\s*\d", normalized) or re.fullmatch(r"(?:[-+]?\d[\d ,.]*\s*)?(?:zl|gr|m2|m²)", normalized):
            block.kind = "information"
            reason = "legal reference or printed rate/unit, not empty answer"
        elif re.match(r"(?:wojt\b|burmistrz\b|urzad (?:gminy|miasta|miejski)|prezydent miasta|starosta\b)", normalized) and not BLANK.search(text):
            block.kind = "information"
            reason = "fixed recipient authority"
        elif re.match(r"(?:ul\.|al\.|\d{2}-\d{3}\s)", normalized) and re.search(r"\d", text) and not BLANK.search(text):
            block.kind = "information"
            reason = "literal address value, no source input label"
        elif re.fullmatch(r"informacje:?|oswiadczenia:?", normalized):
            block.kind = "heading"
            reason = "static information heading"
        elif (
            (len(text) > 130 and not BLANK.search(text) and not START.match(text))
            or re.match(r"(?:podstawa prawna|na podstawie art\.|obja[śs]nienia|w terminie|opłata stanowi|ustalonej uchwałą)", normalized)
            and not BLANK.search(text)
        ):
            block.kind = "legal" if re.search(r"art\.|ustaw|praw|przetwarz|administrator|rodo", normalized) else "instruction"
            reason = "long explanatory prose without explicit answer marker"
        elif text.startswith("(") and re.search(r"w przypadku|opcjonalnie|postaw|nie sa obowiazkowe", normalized):
            block.kind = "instruction"
            reason = "parenthetical guidance"
        if reason:
            block.metadata["role_reason"] = reason
            block.metadata.pop("label_input_pair", None)
        if re.search(r"zalaczniki do wniosku|wymagane zalaczniki|wykaz zalacznikow", normalized):
            attachments = True
        elif block.kind == "heading" and not re.search(r"zalacz", normalized):
            attachments = False
        if (
            attachments
            and block.kind != "legal"
            and re.match(r"^[-–•]\s*(?:ogolny plan|szczegolowy|zatwierdzony projekt|informacj|oryginal|kopia|odpis|dokument|zaswiadczeni|harmonogram)", normalized)
        ):
            block.text = re.sub(r"^[-–•]\s*", "", text)
            block.kind = "form_field"
            block.metadata.update(native_type="attachment", choice_evidence="Document item explicitly listed in source attachment section", requires_review=True, source_text=text)
        output.append(block)
    # Preserve a dotted answer after a checkbox as a separate dependent input.
    # OCR often omits the dots from text, so use the actual raster region.
    details = []
    for block in output:
        if block.kind != "form_field" or block.metadata.get("native_type") != "checkbox":
            continue
        peers = [
            b
            for b in output
            if b is not block
            and b.page == block.page
            and fold(b.text) == fold(block.text)
            and b.metadata.get("label_input_pair")
            and b.metadata.get("input_bbox")
            and b.bbox == block.bbox
        ]
        if peers:
            peer = peers[0]
            peer.kind = "information"
            details.append(
                Block(
                    id=block.id + "_answer",
                    text=block.text + " – doprecyzowanie",
                    page=block.page,
                    bbox=block.bbox,
                    kind="form_field",
                    method=block.method + "+dotted_answer",
                    confidence=0.65,
                    metadata={
                        "native_type": "text",
                        "show_if_block": block.id,
                        "show_if_value": True,
                        "input_bbox": peer.metadata["input_bbox"],
                        "source_text": block.text,
                        "choice_evidence": "Physical dotted answer region associated with source choice; SHOW requires review",
                        "requires_review": True,
                    },
                )
            )
    output.extend(details)
    for block in output:
        if block.kind == "text" and block.text.rstrip().endswith((":", "*")) and not BLANK.search(block.text) and not block.metadata.get("label_input_pair"):
            following = [
                b
                for b in output
                if b.page == block.page and b.kind == "form_field" and b.metadata.get("native_type") == "checkbox" and b.bbox and block.bbox and 0 < b.bbox[1] - block.bbox[3] < 150
            ]
            if len(following) >= 2:
                block.kind = "heading"
                block.metadata["role_reason"] = "Source question introduces physically marked alternatives"
    # A label and inline options may be separate PDF text objects, even on the
    # same baseline. Recover that relationship before treating each glyph alone.
    for block in output:
        matches = list(CHOICE.finditer(block.text))
        if len(matches) < 2 or block.kind == "legal" or block.text[: matches[0].start()].strip():
            continue
        nearby = [
            b
            for b in output
            if b.page == block.page
            and b.bbox
            and block.bbox
            and b.bbox[2] <= block.bbox[0] + 5
            and abs((b.bbox[1] + b.bbox[3] - block.bbox[1] - block.bbox[3]) / 2) < 10
            and re.search(r"plec|wybierz|tryb|wariant", fold(b.text))
        ]
        if nearby:
            label = min(nearby, key=lambda b: block.bbox[0] - b.bbox[2])
            original = block.text
            block.text = label.text.strip(" :*")
            block.kind = "form_field"
            block.metadata.update(
                native_type="radio",
                options=[m.group(1).strip(" .:;") for m in matches],
                source_text=label.text + " " + original,
                choice_evidence="Exclusive label and inline marked alternatives share a geometric baseline",
            )
            label.kind = "information"
    # Consecutive standalone options: group only with explicit exclusive context.
    i = 0
    while i < len(output):
        block = output[i]
        if block.kind == "legal" or not START.match(block.text):
            i += 1
            continue
        run = []
        j = i
        while j < len(output) and output[j].page == block.page and START.match(output[j].text) and output[j].kind != "legal":
            run.append(output[j])
            j += 1
        context = next((b for b in reversed(output[max(0, i - 3) : i]) if b.kind != "blank"), None)
        context_text = context.text if context else ""
        exclusive = bool(re.search(r"plec\b|wybran.*pol|jedn[ao]|sposob (?:zwrotu|korespondencji)|wnioskodawca|wlasciwa kratke", fold(context_text)))
        options = [BLANK.sub("", START.match(b.text).group(1)).strip(" .:*;") for b in run]
        if len(run) > 1 and context and exclusive and len(context_text) < 300:
            context.kind = "form_field"
            context.method += "+choice_group"
            context.metadata.update(native_type="radio", options=options, choice_evidence="Exclusive source context followed by adjacent marked alternatives")
            for b in run:
                b.kind = "information"
                b.metadata["choice_consumed"] = True
        else:
            if len(run) > 1 and context and context_text.rstrip().endswith((":", "*")) and not BLANK.search(context_text):
                context.kind = "heading"
                context.metadata["role_reason"] = "Header of adjacent checkbox options, not an independent answer"
            for b, option in zip(run, options):
                original = b.text
                b.text = option
                b.kind = "form_field"
                b.metadata.update(native_type="checkbox", choice_evidence="Explicit source checkbox glyph", source_text=original)
                if BLANK.search(original):
                    detail = Block(
                        id=b.id + "_detail",
                        text=option + " – doprecyzowanie",
                        page=b.page,
                        bbox=b.bbox,
                        kind="form_field",
                        method=b.method + "+option_detail",
                        confidence=0.75,
                        metadata={
                            "native_type": "text",
                            "show_if_block": b.id,
                            "show_if_value": True,
                            "source_text": original,
                            "choice_evidence": "Blank answer region following this source option; SHOW requires review",
                        },
                    )
                    output.insert(j, detail)
                    j += 1
        i = j
    # Identify genuine vector checkboxes, excluding chains of digit-grid cells.
    for label in output:
        if not label.bbox or not re.fullmatch(r"plec\s*[:*]?", fold(label.text).strip()):
            continue
        choices = [
            b
            for b in output
            if b.page == label.page
            and b.bbox
            and b.kind == "form_field"
            and b.metadata.get("native_type") == "checkbox"
            and b.bbox[0] > label.bbox[2]
            and abs((b.bbox[1] + b.bbox[3] - label.bbox[1] - label.bbox[3]) / 2) < 10
        ]
        if len(choices) >= 2:
            choices.sort(key=lambda b: b.bbox[0])
            label.kind = "form_field"
            label.metadata.update(
                native_type="radio",
                options=[b.text for b in choices],
                source_text=label.text + " " + " ".join(b.metadata.get("source_text", b.text) for b in choices),
                choice_evidence="Single-valued sex label and aligned explicit source alternatives",
            )
            for option in choices:
                option.kind = "information"
                option.metadata["choice_consumed"] = True
    for square in [b for b in output if b.metadata.get("choice_square") and b.bbox]:
        a = square.bbox
        w = a[2] - a[0]
        chain = [b for b in output if b.metadata.get("choice_square") and b.bbox and b.page == square.page and abs(b.bbox[1] - a[1]) < 3 and abs(b.bbox[0] - a[0]) < w * 5]
        if len(chain) >= 4:
            continue
        labels = [
            b
            for b in output
            if b.page == square.page and b.bbox and b.kind == "text" and 0 <= b.bbox[0] - a[2] < 35 and abs((b.bbox[1] + b.bbox[3] - a[1] - a[3]) / 2) < max(10, w)
        ]
        if labels:
            label = min(labels, key=lambda b: b.bbox[0] - a[2])
            label.kind = "form_field"
            label.metadata.update(native_type="checkbox", choice_evidence="Isolated square directly left of source label", input_bbox=a)
    counts = Counter(b.kind for b in output)
    return document.model_copy(update={"blocks": output, "analysis": {**document.analysis, "understanding_v2": {"roles": dict(counts), "source_evidence_only": True}}})
