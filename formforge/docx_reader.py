"""Bounded recursive OOXML reader, including real DrawingML/VML text boxes.

AlternateContent fallback is omitted when a Choice exists. This prevents the
same text from being extracted twice without deleting legitimate repeated data.
Coordinates are document points when anchored; logical layout remains explicit.
"""

import re
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table

MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def text_of(element):
    parts = []
    for node in element.iter():
        if node.tag == qn("w:t"):
            parts.append(node.text or "")
        elif node.tag == qn("w:tab"):
            parts.append("\t")
        elif node.tag == qn("w:br"):
            parts.append("\n")
        elif node.tag == qn("w:sym"):
            char = node.get(qn("w:char"), "").upper()
            parts.append("□" if char in {"F0A8", "F0A7", "F071", "F092", "F0F0"} else "")
    return "".join(parts)


def box_of(textbox):
    ancestors = [textbox, *textbox.iterancestors()]
    for node in ancestors:
        style = node.get("style", "")
        if style:
            values = {k: float(v) for k, v in re.findall(r"([\w-]+):\s*(-?[\d.]+)pt", style)}
            if "width" in values:
                x, y = values.get("margin-left", 0), values.get("margin-top", 0)
                return (x, y, x + values["width"], y + values.get("height", 12))
    anchor = next((n for n in ancestors if n.tag in (f"{{{WP}}}anchor", f"{{{WP}}}inline")), None)
    shape = next((n for n in ancestors if n.tag.endswith("}wsp")), None)
    if anchor is None or shape is None:
        return None

    def number(root, path, key=None, default=0):
        node = root.find(path)
        return float((node.get(key) if key else node.text) or default) if node is not None else default

    x = number(anchor, f"{{{WP}}}positionH/{{{WP}}}posOffset")
    y = number(anchor, f"{{{WP}}}positionV/{{{WP}}}posOffset")
    xfrm = shape.find(f".//{{{A}}}xfrm")
    if xfrm is None:
        return None
    local_x, local_y = number(xfrm, f"{{{A}}}off", "x"), number(xfrm, f"{{{A}}}off", "y")
    width, height = number(xfrm, f"{{{A}}}ext", "cx", 127000), number(xfrm, f"{{{A}}}ext", "cy", 127000)
    for group in shape.iterancestors():
        transform = group.find(f"./*/{{{A}}}xfrm") if group.tag.endswith(("}wgp", "}grpSp")) else None
        if transform is None:
            continue
        sx = number(transform, f"{{{A}}}ext", "cx", 1) / max(1, number(transform, f"{{{A}}}chExt", "cx", 1))
        sy = number(transform, f"{{{A}}}ext", "cy", 1) / max(1, number(transform, f"{{{A}}}chExt", "cy", 1))
        local_x = (local_x - number(transform, f"{{{A}}}chOff", "x")) * sx + number(transform, f"{{{A}}}off", "x")
        local_y = (local_y - number(transform, f"{{{A}}}chOff", "y")) * sy + number(transform, f"{{{A}}}off", "y")
        width, height = width * sx, height * sy
    return tuple(v / 12700 for v in (x + local_x, y + local_y, x + local_x + width, y + local_y + height))


def read_docx(extractor, path):
    document = Document(path)
    body = document.element.body
    for alternate in list(body.iter(f"{{{MC}}}AlternateContent")):
        choice = alternate.find(f"{{{MC}}}Choice")
        fallback = alternate.find(f"{{{MC}}}Fallback")
        selected = choice if choice is not None else fallback
        if selected is not None:
            parent = alternate.getparent()
            index = parent.index(alternate)
            for child in list(selected):
                parent.insert(index, child)
                index += 1
            parent.remove(alternate)
    page_id = extractor.page("Strona 1", source="docx_logical")
    page_marker = None
    extractor.warnings.append("DOCX: strony logiczne i współrzędne kotwic; bez silnika składu Word.")

    def paragraph(node, parent, metadata=None, bbox=None, method="docx_paragraph"):
        nonlocal page_id, page_marker
        # Text box paragraphs are handled separately, never flattened twice.
        boxes = list(node.iter(qn("w:txbxContent")))
        empty_shapes = [shape for shape in node.iter() if shape.tag.endswith(("}wsp", "}rect", "}line")) and shape.find(".//" + qn("w:txbxContent")) is None]
        markers = [re.fullmatch(r"(?:strona\s+)?(\d{1,2})\s*/\s*(\d{1,2})", text_of(box).strip(), re.I) for box in boxes]
        marker = next((m.group(1) for m in markers if m), None)
        if marker and page_marker and marker != page_marker:
            page_id = extractor.page(f"Strona {len(extractor.pages) + 1}", source="docx_logical")
        if marker:
            page_marker = marker
        for shape in empty_shapes:
            rect = box_of(shape)
            if not rect:
                continue
            w, h = rect[2] - rect[0], rect[3] - rect[1]
            if 8 < w < 600 and 0 < h < 140:
                extractor.add("___", page_id, kind="blank", method="docx_drawing", bbox=rect, metadata={"input_region": True, "choice_square": 8 < w < 28 and 8 < h < 28})
        detached = []
        for box in boxes:
            container = box.getparent()
            detached.append((container, container.index(box), box, box_of(box)))
            container.remove(box)
        para = Paragraph(node, parent)
        if para.paragraph_format.page_break_before and extractor.blocks:
            page_id = extractor.page(f"Strona {len(extractor.pages) + 1}", source="docx_logical")
        kind = "heading" if para.style and para.style.name.startswith(("Heading", "Title", "Nagłówek")) else "text"
        info = dict(metadata or {})
        info["bold"] = bool(para.runs) and all(r.bold for r in para.runs if r.text.strip())
        extractor.add(text_of(node), page_id, kind="cell" if metadata else kind, method=method, metadata=info, bbox=bbox)
        for container, index, box, rect in detached:
            container.insert(index, box)
            paragraphs = list(box.iter(qn("w:p")))
            for pi, p in enumerate(paragraphs):
                local = None
                if rect:
                    step = max(8, (rect[3] - rect[1]) / max(1, len(paragraphs)))
                    local = (rect[0], rect[1] + pi * step, rect[2], rect[1] + (pi + 1) * step)
                extractor.add(text_of(p), page_id, bbox=local, method="docx_textbox", metadata={"anchored": bool(rect)})
        for br in node.iter(qn("w:br")):
            if br.get(qn("w:type")) == "page":
                page_id = extractor.page(f"Strona {len(extractor.pages) + 1}", source="docx_logical")

    def walk(container, parent, depth=0, prefix="body"):
        if depth > 12:
            extractor.warnings.append("Pominięto zbyt głęboko zagnieżdżoną tabelę DOCX.")
            return
        for index, node in enumerate(container):
            if node.tag == qn("w:p"):
                paragraph(node, parent)
            elif node.tag == qn("w:tbl"):
                table = Table(node, parent)
                seen = set()
                for ri, row in enumerate(table.rows):
                    for ci, cell in enumerate(row.cells):
                        if cell._tc in seen:
                            continue
                        seen.add(cell._tc)
                        meta = {
                            "table_id": f"{prefix}/t{index}",
                            "row": ri + 1,
                            "column": ci + 1,
                            "paired_blank": ci + 1 < len(row.cells) and not row.cells[ci + 1].text.strip(),
                            "nested_depth": depth,
                        }
                        for child in cell._tc:
                            if child.tag == qn("w:p"):
                                paragraph(child, cell, meta, method="docx_table")
                            elif child.tag == qn("w:tbl"):
                                walk([child], cell, depth + 1, f"{prefix}/t{index}/r{ri}c{ci}")
            elif node.tag == qn("w:sdt"):
                props = node.find(qn("w:sdtPr"))
                alias = props.find(qn("w:alias")) if props is not None else None
                content = node.find(qn("w:sdtContent"))
                if alias is not None:
                    extractor.add(alias.get(qn("w:val")), page_id, kind="form_field", method="docx_content_control", metadata={"native_type": "text"})
                elif content is not None:
                    walk(content, parent, depth + 1, prefix + "/sdt")

    walk(body, document)
