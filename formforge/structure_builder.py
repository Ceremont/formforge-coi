import re
from hashlib import sha256

from .layout_analyzer import fold
from .models import ExtractedDocument, Form, FormField, Section, FieldGroup


class FormStructureBuilder:
    def build(self, document: ExtractedDocument, fields: list[FormField]) -> Form:
        first_blocks = document.blocks[:100]
        title_candidate = next((b for b in first_blocks if re.match(r"^(wniosek|deklaracja|zgloszenie|oswiadczenie|formularz)\b", fold(b.text)) and len(b.text) < 180), None)
        title_block = next((b for b in first_blocks if b.kind == "heading" and re.search(r"wniosek|formularz|zgloszenie|oswiadczenie", fold(b.text))), None)
        if title_block is None:
            title_block = next((b for b in first_blocks if b.kind == "heading"), None)
        if title_candidate:
            title_block = title_candidate
        title = (
            title_block.text
            if title_block
            else next((b.text for b in first_blocks if len(b.text) < 150 and not re.search(r"[:_]{1,}|\.{3,}", b.text)), "Formularz bez rozpoznanego tytułu")
        )
        if title_block and fold(title).strip() in ("wniosek", "deklaracja", "zgloszenie", "oswiadczenie", "formularz"):
            following = first_blocks[first_blocks.index(title_block) + 1 : first_blocks.index(title_block) + 4]
            subtitle = next((b.text for b in following if re.match(r"^(o |w sprawie |dotycz)", fold(b.text))), None)
            if subtitle:
                title += " " + subtitle
        sections = []
        for page in document.pages:
            section = None
            page_blocks = [b for b in document.blocks if b.page == page.id]
            for block in page_blocks:
                if block.kind == "heading" and block != title_block:
                    section = Section(id=f"s{len(sections) + 1}", title=block.text, page=page.id, order=len(sections))
                    sections.append(section)
                matches = [f for f in fields if f.source_reference.block_id == block.id]
                if section is None and (matches or block != title_block):
                    section = Section(id=f"s{len(sections) + 1}", title="Dane formularza" if page.id == 1 else page.title, page=page.id, order=len(sections))
                    sections.append(section)
                for field in matches:
                    field.section = section.id
                if section and not matches and block.kind not in ("heading", "blank") and not block.metadata.get("formula"):
                    section.instructions.append(block.text)
            if section is None:
                sections.append(Section(id=f"s{len(sections) + 1}", title=page.title, page=page.id, order=len(sections)))
        from .conditions import ConditionalRulesBuilder

        recognized = ConditionalRulesBuilder().apply(document, fields, sections)
        for order, field in enumerate(fields):
            field.order = order
        warnings = list(document.warnings)
        if not fields:
            warnings.append("Nie rozpoznano pól. Dokument może zawierać wyłącznie tekst informacyjny; wymagana weryfikacja.")
        for block in document.blocks:
            if re.search(r"\b(jezeli|jesli|w przypadku|o ile)\b", fold(block.text)) and block.id not in recognized:
                warnings.append("Potencjalna zależność wymaga weryfikacji: " + block.text[:200])
        groups = []
        source = {b.id: b for b in document.blocks}
        for section in sections:
            rows = {}
            for field in [f for f in fields if f.section == section.id]:
                block = source[field.source_reference.block_id]
                if block.metadata.get("table_id"):
                    rows.setdefault(block.metadata.get("row", 0), []).append(field)
            for row, members in rows.items():
                if len(members) > 1:
                    group = FieldGroup(id=f"g_{section.id}_{row}", title=f"Wiersz {row}", section=section.id, repeat_key="table_row")
                    groups.append(group)
                    for member in members:
                        member.group_id = group.id
        return Form(
            id="form_" + sha256("\n".join(b.text for b in document.blocks).encode()).hexdigest()[:16],
            title=title,
            pages=document.pages,
            sections=sections,
            fields=fields,
            warnings=warnings,
            groups=groups,
        )

    def _conditions(self, document, fields):
        from .models import ConditionalRule

        # Narrow, explicit syntax only: Jeżeli „Tryb” = „Tak”, pokaż „NIP”.
        pattern = re.compile(r'Jeżeli\s+[„"]([^”"]+)[”"]\s*=\s*[„"]([^”"]+)[”"],?\s+pokaż\s+[„"]([^”"]+)[”"]', re.I)
        by_label = {fold(f.label): f for f in fields}
        for block in document.blocks:
            match = pattern.search(block.text)
            if not match:
                continue
            parent_label, value, target_label = match.groups()
            parent, target = by_label.get(fold(parent_label)), by_label.get(fold(target_label))
            if parent and target and parent.id != target.id and (value in parent.options or parent.field_type == "checkbox" and value.lower() in ("true", "false")):
                if target.id not in [c.field_id for c in parent.conditions]:
                    target.conditions.append(ConditionalRule(field_id=parent.id, value=(value.lower() == "true") if parent.field_type == "checkbox" else value))
