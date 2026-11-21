"""Format adapters. No network, macro execution, or formula evaluation."""

import math
import shutil
import warnings
from contextlib import closing
from pathlib import Path
from time import monotonic

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
        self.started = monotonic()

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
            elif extension == "doc":
                from .legacy_doc import read_doc

                read_doc(self, path)
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
                    native_text = reader.pages[i].extract_text() or ""
                    self.analysis.setdefault("page_text", []).append({"page": page_id, "text": native_text[:200000]})
                    start = len(self.blocks)
                    with closing(page.get_textpage()) as textpage:
                        from .pdf_text import lines

                        for text, box in lines(textpage, height):
                            self.add(text, page_id, bbox=box, method="pdf_text")
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
                        inside = [
                            b
                            for b in self.blocks
                            if b.page == page_id and b.kind != "blank" and b.bbox and box[0] <= b.bbox[0] and box[1] <= b.bbox[1] and box[2] >= b.bbox[2] and box[3] >= b.bbox[3]
                        ]
                        if inside:
                            bottom = max(b.bbox[3] for b in inside)
                            if box[3] - bottom < max(10, (box[3] - box[1]) * 0.25) or sum(len(b.text) for b in inside) > 200:
                                continue
                            box = (box[0], bottom + 2, box[2], box[3])
                        w, h = box[2] - box[0], box[3] - box[1]
                        self.add("___", page_id, kind="blank", bbox=box, method="pdf_vector", metadata={"input_region": True, "choice_square": 8 < w < 28 and 8 < h < 28})
                    if sum(len(b.text) for b in self.blocks[start:] if b.kind != "blank") < 20 or len(native_text) < 1000 and len(reader.pages[i].images) > 0:
                        scale = min(2.5, math.sqrt(self.settings.max_image_pixels / max(width * height, 1)))
                        bitmap = page.render(scale=scale)
                        try:
                            try:
                                self.ocr(bitmap.to_pil(), page_id, coordinate_scale=1 / scale)
                            except DocumentError as error:
                                if error.code not in ("ocr_timeout", "no_text") or not self.blocks:
                                    raise
                                self.warnings.append(f"Częściowy odczyt: strona {page_id}: {error.code}.")
                        finally:
                            bitmap.close()

    def docx(self, path):
        from .docx_reader import read_docx

        read_docx(self, path)

    def xlsx(self, path):
        from openpyxl import load_workbook

        workbook = load_workbook(path, data_only=False, keep_links=False)
        try:
            count = 0
            for sheet in workbook:
                page_id = self.page(sheet.title, source="sheet")
                merged = [str(r) for r in sheet.merged_cells.ranges]
                # Pinned OpenPyXL stores only materialized cells here. Iterating
                # a styled rectangular extent can manufacture millions of empty
                # cells. Bound actual content instead; archive/memory limits also
                # remain in force. Regression tests cover this pinned API.
                populated = sorted((c for c in sheet._cells.values() if c.value is not None), key=lambda c: (c.row, c.column))
                for cell in populated:
                    count += 1
                    if count > self.settings.max_cells:
                        raise DocumentError("Przekroczono limit komórek.", 413, "cell_limit")
                    formula = cell.data_type == "f"
                    span = next((r for r in sheet.merged_cells.ranges if cell.coordinate in r), None)
                    following = (span.max_col + 1) if span else cell.column + 1
                    next_cell = sheet._cells.get((cell.row, following))
                    next_blank = following <= sheet.max_column and (next_cell is None or next_cell.value is None)
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
                            "column_span": span.max_col - span.min_col + 1 if span else 1,
                            "row_span": span.max_row - span.min_row + 1 if span else 1,
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
                        span = int(cell.getAttribute("numbercolumnsspanned") or 1)
                        next_column = column + repeat
                        following = None
                        for other in nodes[n + 1 :]:
                            if next_column >= column + span:
                                following = other
                                break
                            next_column += int(other.getAttribute("numbercolumnsrepeated") or 1)
                        next_blank = following is not None and not teletype.extractText(following).strip()
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
                                "row_span": cell.getAttribute("numberrowsspanned") or 1,
                            },
                        )
                    column += repeat
        self.warnings.append("ODS: powtórzenia i scalone komórki są metadanymi; formuły nie są wykonywane.")

    def image(self, path):
        # Inspect dimensions before decoding; enforce our explicit source budget
        # rather than letting Pillow mask the reason with a generic warning.
        Image.MAX_IMAGE_PIXELS = None
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as source:
                if source.width * source.height > self.settings.max_source_image_pixels:
                    raise DocumentError("Obraz przekracza limit pikseli.", 413, "pixel_limit")
                if source.width * source.height <= self.settings.max_image_pixels:
                    image = ImageOps.exif_transpose(source).convert("RGB")
                    page_id = self.page("Skan dokumentu", image.width, image.height, "image")
                    self.ocr(image, page_id)
                else:
                    # Bounded sequential OCR tiles preserve the whole source.
                    # Do not downsample a 16-page scan into an unreadable image.
                    from .image_tiles import tiles

                    self.warnings.append("Duży obraz podzielono na logiczne strony OCR; granice wymagają sprawdzenia.")
                    for box in tiles(source, self.settings.max_image_pixels):
                        with source.crop(box) as tile:
                            page_id = self.page(f"Skan {len(self.pages) + 1}", tile.width, tile.height, "image_tile")
                            self.analysis.setdefault("image_tiles", []).append({"page": page_id, "source_bbox": box})
                            try:
                                self.ocr(tile.convert("RGB"), page_id)
                            except DocumentError as error:
                                if error.code not in ("ocr_timeout", "no_text"):
                                    raise
                                self.warnings.append(f"Częściowy odczyt: strona {page_id}: {error.code}.")

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

        remaining = self.settings.processing_timeout - (monotonic() - self.started) - 8
        if remaining < 1:
            raise DocumentError("Wyczerpano budżet OCR; zachowano poprzedni odczyt.", 408, "ocr_timeout")
        bounded = self.settings.model_copy(update={"ocr_timeout": min(self.settings.ocr_timeout, remaining)})
        lines, report = recognize(image, "+".join(available), bounded)
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
            self._selection_margins(gray, page_id, coordinate_scale)
            from .geometry import raster_lines, raster_dotted_lines

            for box in raster_lines(gray):
                self.add("___", page_id, kind="blank", bbox=tuple(v * coordinate_scale for v in box), method="raster_line", metadata={"input_region": True})
            for box in raster_dotted_lines(gray):
                self.add("___", page_id, kind="blank", bbox=tuple(v * coordinate_scale for v in box), method="raster_dotted_line", confidence=0.7, metadata={"input_region": True})

    def _selection_margins(self, image, page_id, scale):
        import re
        from .layout_analyzer import fold

        lines = [b for b in self.blocks if b.page == page_id and b.method == "tesseract_ocr" and b.bbox]
        for i, line in enumerate(lines):
            context = " ".join(b.text for b in lines[max(0, i - 8) : i])
            if not re.search(r"wybierz|zaznacz|prosze.*[o0]:|plec|postaw", fold(context)):
                continue
            a = line.bbox
            left = max(0, int(a[0] / scale) - 50)
            right = max(left, int(a[0] / scale) - 3)
            top = max(0, int(a[1] / scale) - 5)
            bottom = min(image.height, int(a[3] / scale) + 5)
            if right <= left or bottom <= top:
                continue
            crop = image.crop((left, top, right, bottom)).point(lambda p: 255 if p < 140 else 0)
            box = crop.getbbox()
            if box and 8 <= box[2] - box[0] <= 40 and 8 <= box[3] - box[1] <= 40:
                rect = tuple(v * scale for v in (left + box[0], top + box[1], left + box[2], top + box[3]))
                self.add(
                    line.text,
                    page_id,
                    kind="form_field",
                    method="ocr_selection_candidate",
                    bbox=line.bbox,
                    confidence=0.6,
                    metadata={
                        "native_type": "checkbox",
                        "input_bbox": rect,
                        "choice_evidence": "Isolated selection-sized mark left of label in a source choice question; requires review",
                        "requires_review": True,
                    },
                )

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
                        nearby = [
                            b
                            for b in self.blocks
                            if b.page == page_id and b.bbox and abs(b.bbox[1] / scale - y) < size * 1.5 and 0 <= b.bbox[0] / scale - (x + size) < max(40, size * 2)
                        ]
                        if not nearby:
                            # Preserve the physical candidate for inspection,
                            # without inventing an editable label from a letter.
                            self.add(
                                "___",
                                page_id,
                                kind="blank",
                                method="ocr_square_candidate",
                                bbox=(start * scale, y * scale, x * scale, bottom * scale),
                                confidence=0.5,
                                metadata={"input_region": True, "choice_square": True},
                            )
                            continue
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
