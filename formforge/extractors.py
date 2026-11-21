"""Format adapters. No network, macro execution, or formula evaluation."""

import math
import shutil
import warnings
from contextlib import closing
from pathlib import Path

from PIL import Image, ImageOps

from .config import Settings
from .errors import DocumentError
from .models import Block, ExtractedDocument, Page


class DocumentExtractor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.blocks: list[Block] = []
        self.pages: list[Page] = []
        self.warnings: list[str] = []
        self.analysis = {"ocr": []}

    def add(self, text, page, **kwargs):
        text = str(text).strip()
        if not text:
            return
        if len(self.blocks) >= self.settings.max_blocks:
            raise DocumentError("Dokument zawiera zbyt wiele bloków tekstu.", 413, "block_limit")
        if len(text) > 20_000:
            raise DocumentError("Blok tekstu przekracza limit długości.", 413)
        self.blocks.append(Block(id=f"b{len(self.blocks) + 1}", text=text, page=page, **kwargs))

    def page(self, title, width=None, height=None, source="document"):
        if len(self.pages) >= self.settings.max_pages:
            raise DocumentError("Dokument przekracza limit stron lub arkuszy.", 413, "page_limit")
        page = Page(id=len(self.pages) + 1, title=title, width=width, height=height, source=source)
        self.pages.append(page)
        return page.id

    def extract(self, path: Path, filename: str, extension: str) -> ExtractedDocument:
        try:
            if extension == "pdf":
                self.pdf(path)
            elif extension == "docx":
                self.docx(path)
            elif extension == "xlsx":
                self.xlsx(path)
            elif extension == "ods":
                self.ods(path)
            else:
                self.image(path)
        except DocumentError:
            raise
        except Exception as exc:
            raise DocumentError("Nie można odczytać dokumentu. Plik może być uszkodzony lub zaszyfrowany.") from exc
        if not self.blocks:
            raise DocumentError("Nie znaleziono czytelnego tekstu ani pól formularza.", 422, "no_text")
        return ExtractedDocument(filename=filename, format=extension, pages=self.pages, blocks=self.blocks, warnings=self.warnings, analysis=self.analysis)

    def pdf(self, path):
        import pypdfium2 as pdfium
        from pypdf import PdfReader

        reader = PdfReader(path)
        if reader.is_encrypted:
            raise DocumentError("Zaszyfrowane pliki PDF nie są obsługiwane.")
        if len(reader.pages) > self.settings.max_pages:
            raise DocumentError("Przekroczono limit stron PDF.", 413, "page_limit")
        with pdfium.PdfDocument(str(path)) as document:
            for i in range(len(document)):
                with closing(document[i]) as page:
                    width, height = page.get_size()
                    page_id = self.page(f"Strona {i + 1}", width, height)
                    self.analysis.setdefault("page_text", []).append({"page": page_id, "text": reader.pages[i].extract_text()[:200000]})
                    start = len(self.blocks)
                    with closing(page.get_textpage()) as textpage:
                        for n in range(textpage.count_rects()):
                            left, bottom, right, top = textpage.get_rect(n)
                            text = textpage.get_text_bounded(left, bottom, right, top)
                            self.add(text, page_id, bbox=(left, height - top, right, height - bottom), method="pdf_text")
                    # Retain native interactive fields, including coordinates and choices.
                    for annot_ref in reader.pages[i].get("/Annots", []):
                        annot = annot_ref.get_object()
                        parent = annot.get("/Parent", annot).get_object()
                        kind = annot.get("/FT", parent.get("/FT"))
                        label = annot.get("/TU", parent.get("/TU")) or annot.get("/T", parent.get("/T"))
                        if kind and label:
                            flags = int(annot.get("/Ff", parent.get("/Ff", 0)))
                            field_type = {"/Tx": "textarea" if flags & 4096 else "text", "/Ch": "select", "/Btn": "radio" if flags & 32768 else "checkbox"}.get(str(kind), "text")
                            opts = parent.get("/Opt", [])
                            rect = list(annot.get("/Rect", [0, 0, 0, 0]))
                            self.add(
                                str(label),
                                page_id,
                                kind="form_field",
                                method="pdf_acroform",
                                bbox=(float(rect[0]), height - float(rect[3]), float(rect[2]), height - float(rect[1])),
                                metadata={"native_type": field_type, "required": bool(flags & 2), "options": [str(o[-1] if isinstance(o, list) else o) for o in opts]},
                            )
                    from .geometry import pdf_regions

                    for box in pdf_regions(reader.pages[i], height):
                        if any(b.page == page_id and b.bbox and b.kind == "form_field" and abs(b.bbox[0] - box[0]) < 5 and abs(b.bbox[1] - box[1]) < 5 for b in self.blocks):
                            continue
                        if any(b.page == page_id and b.bbox and box[0] <= b.bbox[0] and box[1] <= b.bbox[1] and box[2] >= b.bbox[2] and box[3] >= b.bbox[3] for b in self.blocks):
                            continue
                        self.add("___", page_id, kind="blank", bbox=box, method="pdf_vector", metadata={"input_region": True})
                    if sum(len(b.text) for b in self.blocks[start:] if b.kind != "blank") < 20:
                        scale = min(2.5, math.sqrt(self.settings.max_image_pixels / max(width * height, 1)))
                        bitmap = page.render(scale=scale)
                        try:
                            self.ocr(bitmap.to_pil(), page_id, coordinate_scale=1 / scale)
                        finally:
                            bitmap.close()

    def docx(self, path):
        from docx import Document
        from docx.oxml.ns import qn
        from docx.table import Table
        from docx.text.paragraph import Paragraph

        document = Document(path)
        page_id = self.page("Strona 1", source="docx_logical")
        self.warnings.append("DOCX: podział na strony jest logiczny (jawne podziały), bez silnika składu Word.")
        for element in document.element.body:
            if element.tag == qn("w:p"):
                para = Paragraph(element, document)
                if para.paragraph_format.page_break_before and self.blocks:
                    page_id = self.page(f"Strona {len(self.pages) + 1}", source="docx_logical")
                kind = (
                    "heading"
                    if para.style and para.style.name.startswith(("Heading", "Title", "Nagłówek"))
                    else "list"
                    if element.find(".//" + qn("w:numPr")) is not None
                    else "text"
                )
                self.add(para.text, page_id, kind=kind, method="docx_paragraph")
                for br in element.iter(qn("w:br")):
                    if br.get(qn("w:type")) == "page":
                        page_id = self.page(f"Strona {len(self.pages) + 1}", source="docx_logical")
            elif element.tag == qn("w:tbl"):
                table = Table(element, document)
                for row_index, row in enumerate(table.rows):
                    seen = set()
                    for col_index, cell in enumerate(row.cells):
                        if cell._tc in seen:
                            continue
                        seen.add(cell._tc)
                        if cell.text.strip():
                            next_blank = col_index + 1 < len(row.cells) and not row.cells[col_index + 1].text.strip()
                            self.add(
                                cell.text,
                                page_id,
                                kind="cell",
                                method="docx_table",
                                metadata={
                                    "row": row_index + 1,
                                    "column": col_index + 1,
                                    "paired_blank": next_blank,
                                    "merged": cell._tc.tcPr is not None and cell._tc.tcPr.find(qn("w:gridSpan")) is not None,
                                },
                            )
            elif element.tag == qn("w:sdt"):
                text = " ".join(t.text or "" for t in element.iter(qn("w:t")))
                alias = element.find(".//" + qn("w:alias"))
                label = alias.get(qn("w:val")) if alias is not None else text
                self.add(label, page_id, kind="form_field", method="docx_content_control", metadata={"native_type": "text"})

    def xlsx(self, path):
        from openpyxl import load_workbook

        workbook = load_workbook(path, data_only=False, keep_links=False)
        try:
            count = 0
            for sheet in workbook:
                if sheet.max_row * sheet.max_column > self.settings.max_cells:
                    raise DocumentError("Arkusz przekracza limit liczby komórek.", 413, "cell_limit")
                page_id = self.page(sheet.title, source="sheet")
                merged = [str(r) for r in sheet.merged_cells.ranges]
                for row in sheet:
                    for cell in row:
                        count += 1
                        if count > self.settings.max_cells:
                            raise DocumentError("Przekroczono limit komórek.", 413, "cell_limit")
                        if cell.value is None:
                            continue
                        formula = cell.data_type == "f"
                        next_blank = cell.column < sheet.max_column and sheet.cell(cell.row, cell.column + 1).value is None
                        self.add(
                            cell.value,
                            page_id,
                            kind="cell",
                            method="xlsx_cell",
                            metadata={
                                "sheet": sheet.title,
                                "cell": cell.coordinate,
                                "row": cell.row,
                                "column": cell.column,
                                "paired_blank": next_blank,
                                "formula": str(cell.value) if formula else None,
                                "merged_ranges": merged if cell.row == 1 else [],
                                "bold": bool(cell.font.b),
                            },
                        )
        finally:
            workbook.close()
        self.warnings.append("Formuły arkusza są metadanymi; nie są wykonywane. Ukryte komórki także podlegają analizie.")

    def ods(self, path):
        from odf import teletype
        from odf.opendocument import load
        from odf.table import Table, TableRow

        document = load(str(path))
        count = 0
        for table in document.spreadsheet.getElementsByType(Table):
            title = table.getAttribute("name") or "Arkusz"
            page_id = self.page(title, source="sheet")
            row_number = 0
            for row in table.getElementsByType(TableRow):
                repeat_rows = int(row.getAttribute("numberrowsrepeated") or 1)
                row_number += repeat_rows
                column = 0
                nodes = [c for c in row.childNodes if getattr(c, "qname", (None, None))[1] in ("table-cell", "covered-table-cell")]
                for n, cell in enumerate(nodes):
                    repeat = int(cell.getAttribute("numbercolumnsrepeated") or 1)
                    text = teletype.extractText(cell).strip()
                    formula = cell.getAttribute("formula")
                    # Empty ODF runs describe sparse sheet padding, not materialized
                    # cells. Count stored nodes and bound nonempty repetitions.
                    count += repeat * repeat_rows if text or formula else 1
                    if count > self.settings.max_cells:
                        raise DocumentError("ODS przekracza limit komórek, w tym powtórzeń.", 413, "cell_limit")
                    if text or formula:
                        next_blank = n + 1 < len(nodes) and not teletype.extractText(nodes[n + 1]).strip()
                        self.add(
                            text or formula,
                            page_id,
                            kind="cell",
                            method="ods_cell",
                            metadata={
                                "sheet": title,
                                "cell": f"R{row_number}C{column + 1}",
                                "row": row_number,
                                "column": column + 1,
                                "paired_blank": next_blank,
                                "formula": formula,
                                "row_repeat": repeat_rows,
                                "column_repeat": repeat,
                                "column_span": cell.getAttribute("numbercolumnsspanned") or 1,
                            },
                        )
                    column += repeat
        self.warnings.append("ODS: powtórzenia i scalone komórki są metadanymi; formuły nie są wykonywane.")

    def image(self, path):
        Image.MAX_IMAGE_PIXELS = self.settings.max_image_pixels
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as source:
                if source.width * source.height > self.settings.max_image_pixels:
                    raise DocumentError("Obraz przekracza limit pikseli.", 413, "pixel_limit")
                image = ImageOps.exif_transpose(source).convert("RGB")
                page_id = self.page("Skan dokumentu", image.width, image.height, "image")
                self.ocr(image, page_id)

    def ocr(self, image, page_id, coordinate_scale=1):
        import pytesseract

        if not shutil.which("tesseract"):
            raise DocumentError("Lokalny silnik Tesseract OCR nie jest zainstalowany. Zainstaluj Tesseract z językami pol i eng.", 503, "ocr_unavailable")
        languages = set(pytesseract.get_languages(config=""))
        requested = self.settings.ocr_languages.split("+")
        available = [lang for lang in requested if lang in languages]
        if not available:
            raise DocumentError("Brak lokalnych danych językowych OCR.", 503, "ocr_languages_missing")
        if set(requested) - languages:
            self.warnings.append("OCR: brakuje części danych językowych; użyto " + "+".join(available))
        from .ocr import recognize

        lines, report = recognize(image, "+".join(available), self.settings)
        self.analysis["ocr"].append({"page": page_id, **report})
        for line in lines:
            self.add(
                line["text"],
                page_id,
                bbox=tuple(v * coordinate_scale for v in line["bbox"]),
                method="tesseract_ocr",
                confidence=min(1, max(0, line["confidence"])),
                metadata={"ocr_variant": line["variant"]},
            )
        low = sum(line["confidence"] < 0.65 for line in lines)
        if low:
            self.warnings.append(f"OCR, strona {page_id}: {low} obszarów o niskiej jakości wymaga sprawdzenia w źródle.")
        # Geometric checkbox candidates: isolated small square outlines. Each is
        # explicitly uncertain; no checked state or value is fabricated.
        gray = ImageOps.grayscale(image)
        if gray.width * gray.height <= self.settings.max_image_pixels:
            self._checkbox_candidates(gray, page_id, coordinate_scale)
            from .geometry import raster_lines

            for box in raster_lines(gray):
                self.add("___", page_id, kind="blank", bbox=tuple(v * coordinate_scale for v in box), method="raster_line", metadata={"input_region": True})

    def _checkbox_candidates(self, image, page_id, scale):
        # Scan sparse horizontal dark runs, then verify four sides and empty center.
        pixels = image.load()
        candidates = []
        for y in range(2, image.height - 12, 2):
            x = 2
            while x < image.width - 12:
                if pixels[x, y] > 100:
                    x += 2
                    continue
                start = x
                while x < image.width and pixels[x, y] < 100:
                    x += 1
                size = x - start
                if 10 <= size <= 45 and y + size < image.height:
                    bottom = y + size - 1
                    horizontal = sum(pixels[t, bottom] < 140 for t in range(start, x)) / size
                    vertical = sum(pixels[start, t] < 140 and pixels[x - 1, t] < 140 for t in range(y, bottom + 1)) / size
                    center = pixels[start + size // 2, y + size // 2]
                    if horizontal > 0.65 and vertical > 0.65 and center > 180 and not any(abs(start - a) < size and abs(y - b) < size for a, b in candidates):
                        candidates.append((start, y))
                        nearby = [b for b in self.blocks if b.page == page_id and b.bbox and abs(b.bbox[1] / scale - y) < size * 1.5 and b.bbox[2] / scale > x]
                        label = min(nearby, key=lambda b: abs(b.bbox[1] / scale - y)).text if nearby else "Pole wyboru (do weryfikacji)"
                        self.add(
                            label,
                            page_id,
                            kind="form_field",
                            method="ocr_square_candidate",
                            confidence=0.55,
                            bbox=(start * scale, y * scale, x * scale, bottom * scale),
                            metadata={"native_type": "checkbox"},
                        )
                x += 2
