import re
import statistics
import unicodedata
from collections import Counter

from .models import ExtractedDocument


def fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower().replace("ł", "l")) if not unicodedata.combining(c))


LABEL = re.compile(
    r"^(?:imie(?: i nazwisko)?|nazwisko|(?:(?:numer|nr\.?)\s+)?(?:pesel|nip|regon|krs)|e-?mail|telefon|data(?: urodzenia| zlozenia)?|kod pocztowy|adres(?: zamieszkania)?|miejscowosc|ulica|(?:numer|nr\.?) domu|(?:numer|nr\.?) lokalu|poczta)\s*[:*]?$",
    re.I,
)


class LayoutAnalyzer:
    """Geometry augments existing readers and preserves all source blocks."""

    def analyze(self, document: ExtractedDocument) -> ExtractedDocument:
        blocks = []
        legal_area = False
        for page in document.pages:
            source = [b.model_copy(deep=True) for b in document.blocks if b.page == page.id]
            heights = [b.bbox[3] - b.bbox[1] for b in source if b.bbox and b.kind != "blank" and b.bbox[3] > b.bbox[1]]
            median = statistics.median(heights) if heights else 12
            source = self._columns(source, page.width, median)
            for block in source:
                text = block.text.strip()
                normalized = fold(text)
                if re.search(r"^(klauzula informacyjna|informacja o przetwarzaniu danych|obowiazek informacyjny)", normalized):
                    legal_area = True
                elif re.match(r"^(wniosek|deklaracja|formularz|zgloszenie)\b", normalized) and len(text) < 120:
                    legal_area = False
                if legal_area:
                    block.kind = "legal"
                    block.metadata["legal_area"] = True
                    continue
                if block.kind in ("form_field", "heading", "blank"):
                    continue
                thematic = re.fullmatch(
                    r"(?:dane (?:wnioskodawcy|osobowe|kontaktowe|ucznia|przedstawiciela)|sposob i forma udostepnienia informacji|zalaczniki)\s*[:* ]*", normalized
                )
                if thematic:
                    block.kind = "heading"
                    block.metadata["role_reason"] = "Thematic caption without an answer marker"
                elif re.fullmatch(r"[_ .…\-]{3,}", text):
                    block.kind = "blank"
                elif re.match(r"^(uwaga|instrukcja|nalezy|wypelnij|prosimy)\b", normalized):
                    block.kind = "instruction"
                elif re.match(r"^(podstawa prawna|pouczenie|rodo|administratorem danych|zgodnie z art)", normalized):
                    block.kind = "legal"
                elif not LABEL.fullmatch(re.sub(r"(?<=[a-z])\d{1,2}\b", "", re.sub(r"^(?:[ivx]{1,5}|\d{1,2})[.)]\s*", "", normalized)).strip(" /*:()")):
                    numbered = re.match(r"^(?:[ivx]{1,5}|\d{1,2})[.)]\s+(?:dane|informacje|instrukcja|oswiadczeni|zalaczniki|podpis)\b", normalized)
                    upper = text.isupper() and 3 < len(text) < 90 and not re.search(r"[:*]|[_:.]{2,}", text)
                    large = block.bbox and block.bbox[3] - block.bbox[1] > median * 1.35
                    if (numbered or upper or large or block.metadata.get("bold")) and len(text) < 110 and not re.search(r"[:_…]|\.{3,}", text):
                        block.kind = "heading"
            self._associate(source, median)
            ordered = self._columns(source, page.width, median)
            for block in ordered:
                if block.kind == "cell":
                    block.metadata.setdefault("table_id", f"table_p{page.id}")
            blocks.extend(ordered)
        counts = Counter(fold(b.text) for b in blocks if b.kind == "heading")
        for block in blocks:
            if block.kind == "heading" and counts[fold(block.text)] > 1:
                block.metadata["repeated_heading"] = True
        analysis = {
            **document.analysis,
            "layout": {
                "geometry_associations": sum(bool(b.metadata.get("label_input_pair")) for b in blocks),
                "columns": len({(b.page, b.metadata.get("column", 0)) for b in blocks}),
                "repeated_headings": [text for text, n in counts.items() if n > 1],
            },
        }
        return document.model_copy(update={"blocks": blocks, "analysis": analysis})

    def _associate(self, blocks, median):
        for blank in [b for b in blocks if b.kind == "blank"]:
            candidates = []
            for label in blocks:
                if label.kind not in ("text", "cell") or len(label.text) > 150 or re.search(r"\.{3,}|_{3,}", label.text):
                    continue
                if blank.bbox and label.bbox:
                    a, b = label.bbox, blank.bbox
                    if b[0] <= a[0] and b[1] <= a[1] and b[2] >= a[2] and b[3] >= a[3]:
                        continue
                    center = abs((a[1] + a[3] - b[1] - b[3]) / 2)
                    horizontal = max(0, a[0] - b[2], b[0] - a[2])
                    above = b[1] - a[3]
                    overlap = max(0, min(a[2], b[2]) - max(a[0], b[0])) / max(1, a[2] - a[0])
                    if a[2] <= b[0] + 5 and center < max(median * 1.4, (b[3] - b[1]) / 2 + median) and horizontal < 100:
                        candidates.append((horizontal + center * 2, label))
                    elif -3 <= above <= max(36, median * 3) and overlap > 0.35:
                        candidates.append((above * 2 + abs(a[0] - b[0]) * 0.2 + 10, label))
                elif not blank.bbox and blocks.index(blank) == blocks.index(label) + 1:
                    candidates.append((10, label))
                caption = label.text.strip().startswith(("(", "/")) or bool(re.match(r"^(nazwisko|imie|adres|rodzaj|nr telefonu)", fold(label.text)))
                if caption and blank.bbox and label.bbox:
                    a, b = label.bbox, blank.bbox
                    below = a[1] - b[3]
                    overlap = max(0, min(a[2], b[2]) - max(a[0], b[0])) / max(1, a[2] - a[0])
                    if -2 <= below <= max(25, median * 2) and overlap > 0.35:
                        candidates.append((max(0, below) + 2, label))
                elif caption and not blank.bbox and blocks.index(label) == blocks.index(blank) + 1:
                    candidates.append((4, label))
            if candidates:
                _, label = min(candidates, key=lambda item: item[0])
                previous = label.metadata.get("input_bbox")
                label.metadata["label_input_pair"] = True
                label.metadata["blank_lines"] = label.metadata.get("blank_lines", 0) + 1
                if label.metadata["blank_lines"] > 1:
                    label.metadata["multiline"] = True
                label.metadata["input_bbox"] = list(blank.bbox) if blank.bbox else None
                if previous and blank.bbox:
                    label.metadata["input_bbox"] = [
                        min(previous[0], blank.bbox[0]),
                        min(previous[1], blank.bbox[1]),
                        max(previous[2], blank.bbox[2]),
                        max(previous[3], blank.bbox[3]),
                    ]
                    label.metadata["multiline"] = True
                blank.metadata["label_block_id"] = label.id

    def _columns(self, blocks, width, median):
        text = [b for b in blocks if b.bbox and b.kind not in ("blank", "heading", "form_field")]
        if not text:
            return blocks
        width = width or max(b.bbox[2] for b in text)
        sorted_text = sorted(text, key=lambda b: b.bbox[0])
        cuts = []
        for left, right in zip(sorted_text, sorted_text[1:]):
            cut = (left.bbox[2] + right.bbox[0]) / 2
            lhs = [b for b in text if b.bbox[2] <= cut]
            rhs = [b for b in text if b.bbox[0] >= cut]
            if len(lhs) >= 2 and len(rhs) >= 2 and len(lhs) + len(rhs) == len(text):
                gap = min(b.bbox[0] for b in rhs) - max(b.bbox[2] for b in lhs)
                if gap > max(25, width * 0.05):
                    cuts.append((gap, cut))
        cut = max(cuts)[1] if cuts else None
        for b in blocks:
            b.metadata["column"] = 1 if cut and b.bbox and b.bbox[0] >= cut else 0
        if cut:
            headings = sorted([b for b in blocks if b.kind == "heading" and b.bbox], key=lambda b: b.bbox[1])

            def key(b):
                if not b.bbox:
                    return (0, 0, 0, 0)
                band = sum(h.bbox[1] < b.bbox[1] - 2 for h in headings)
                return (band, -1 if b.kind == "heading" else b.metadata["column"], b.bbox[1], b.bbox[0])

            return sorted(blocks, key=key)
        return sorted(blocks, key=lambda b: (round(b.bbox[1] / max(3, median / 2)), b.bbox[0]) if b.bbox else (blocks.index(b) * median, 0))
