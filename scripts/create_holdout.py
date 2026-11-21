"""One-time independent synthetic holdout authoring. Never imports the engine.

Refuses to overwrite a frozen dataset. Expected labels/types/sections come from
the authored source, not predictions. Do not tune recognition after evaluation.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableCell, TableRow
from odf.text import P
from openpyxl import Workbook
from openpyxl.styles import PatternFill
from PIL import Image, ImageDraw, ImageEnhance, ImageFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation/holdout-v1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if (OUT / "manifest.json").exists():
        raise SystemExit("Holdout already frozen; do not overwrite or retune against it")
    OUT.mkdir(parents=True, exist_ok=True)
    font = next(p for p in [Path("/System/Library/Fonts/Supplemental/Arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")] if p.exists())
    pdfmetrics.registerFont(TTFont("Holdout", str(font)))
    cases = []

    def record(name, fields, ocr=False, features=()):
        cases.append({"file": name, "fields": fields, "ocr": ocr, "features": list(features), "sha256": digest(OUT / name)})

    def field(label, kind, section, page=1):
        return {"label": label, "field_type": kind, "section": section, "page": page}

    def pdf_form(name, title, sections, columns=False):
        pdf = canvas.Canvas(str(OUT / name), pagesize=(600, 820))
        pdf.setFont("Holdout", 15)
        pdf.drawString(42, 775, title)
        expected = []
        y = 720
        for section, items in sections:
            pdf.setFont("Holdout", 12)
            pdf.drawString(42, y, section)
            y -= 48
            for index, (label, kind) in enumerate(items):
                if columns:
                    x = 42 + (index % 2) * 285
                    row_y = y - (index // 2) * 85
                else:
                    x, row_y = 42, y - index * 65
                pdf.setFont("Holdout", 10)
                pdf.drawString(x, row_y, label)
                pdf.line(x, row_y - 20, x + 220, row_y - 20)
                expected.append(field(label, kind, section))
            y -= ((len(items) + 1) // 2 * 85 if columns else len(items) * 65) + 35
        pdf.save()
        return expected

    expected = pdf_form(
        "oswiadczenie.pdf", "OŚWIADCZENIE O AKTUALIZACJI DANYCH", [("A. OSOBA", [("Imię", "text"), ("Nazwisko", "text"), ("PESEL", "pesel"), ("Data urodzenia", "date")])], True
    )
    record("oswiadczenie.pdf", expected, features=["two_columns", "labels_above_lines", "no_colons"])
    expected = pdf_form(
        "obszar.pdf", "KARTA PODMIOTU", [("IDENTYFIKACJA", [("NIP", "nip"), ("REGON", "regon"), ("Kod pocztowy", "postal_code"), ("Adres siedziby", "address")])], True
    )
    record("obszar.pdf", expected, features=["no_colons", "negative_whitespace", "tax_identifiers"])
    doc = Document()
    doc.add_heading("KARTA WERYFIKACJI UPRAWNIEŃ", 0)
    doc.add_heading("DANE OSOBY", 1)
    items = [("Imię", "text"), ("Nazwisko", "text"), ("Data urodzenia", "date"), ("Adres korespondencyjny", "address"), ("NIP", "nip")]
    table = doc.add_table(rows=0, cols=2)
    for label, _ in items:
        cells = table.add_row().cells
        cells[0].text = label
    doc.add_paragraph("Podstawa prawna: dane służą wyłącznie obsłudze sprawy.")
    doc.save(OUT / "uprawnienia.docx")
    record("uprawnienia.docx", [field(a, b, "DANE OSOBY") for a, b in items], features=["table_labels", "no_colons", "legal_negative_control"])
    book = Workbook()
    sheet = book.active
    sheet.title = "Rejestr"
    sheet.append(["REJESTR INTERESANTÓW"])
    sheet.append(["DANE KONTAKTOWE"])
    items = [
        ("Nazwa jednostki", "text"),
        ("REGON", "regon"),
        ("Adres e-mail", "email"),
        ("Numer telefonu", "phone"),
        ("Kod pocztowy", "postal_code"),
        ("Adres siedziby", "address"),
    ]
    for i, (label, _) in enumerate(items, 3):
        sheet.cell(i, 1, label)
        sheet.cell(i, 2).fill = PatternFill("solid", fgColor="EEEEEE")
    book.save(OUT / "rejestr.xlsx")
    record("rejestr.xlsx", [field(a, b, "DANE KONTAKTOWE") for a, b in items], features=["spreadsheet", "empty_adjacent_cells"])
    doc = OpenDocumentSpreadsheet()
    table = Table(name="Karta")
    items = [("Nazwa podmiotu", "text"), ("NIP", "nip"), ("REGON", "regon"), ("Kwota opłaty", "number"), ("Termin realizacji (RRRR-MM-DD)", "date")]
    for label in ["KARTA OPŁAT", "DANE PŁATNIKA"] + [a for a, _ in items]:
        row = TableRow()
        cell = TableCell(valuetype="string")
        cell.addElement(P(text=label))
        row.addElement(cell)
        row.addElement(TableCell())
        table.addElement(row)
    doc.spreadsheet.addElement(table)
    doc.save(str(OUT / "oplaty.ods"))
    record("oplaty.ods", [field(a, b, "DANE PŁATNIKA") for a, b in items], features=["ods", "date_format_hint"])
    pdf = canvas.Canvas(str(OUT / "rodzina.pdf"), pagesize=(600, 820))
    expected = []
    for page in range(1, 4):
        pdf.setFont("Holdout", 14)
        pdf.drawString(42, 775, "KWESTIONARIUSZ OSÓB UPRAWNIONYCH" if page == 1 else f"OSOBA {page}")
        section = f"OSOBA {page}"
        pdf.setFont("Holdout", 12)
        pdf.drawString(42, 725, section)
        for i, (label, kind) in enumerate([("Imię", "text"), ("Nazwisko", "text"), ("Data urodzenia", "date"), ("Adres", "address")]):
            y = 675 - i * 80
            pdf.setFont("Holdout", 10)
            pdf.drawString(42, y, label)
            pdf.rect(42, y - 36, 470, 25)
            expected.append(field(label, kind, section, page))
        pdf.showPage()
    pdf.save()
    record("rodzina.pdf", expected, features=["multipage", "repeated_fields", "boxed_inputs"])
    doc = Document()
    doc.add_heading("INFORMACJA O ZDARZENIU", 0)
    doc.add_heading("OPIS ZDARZENIA", 1)
    doc.add_paragraph("Opis okoliczności")
    doc.add_paragraph("_" * 40)
    doc.add_paragraph("_" * 40)
    doc.add_paragraph("_" * 40)
    doc.add_paragraph("Załącznik: __________")
    doc.add_paragraph("Data zdarzenia: __________")
    doc.save(OUT / "zdarzenie.docx")
    record(
        "zdarzenie.docx",
        [field("Opis okoliczności", "textarea", "OPIS ZDARZENIA"), field("Załącznik", "attachment", "OPIS ZDARZENIA"), field("Data zdarzenia", "date", "OPIS ZDARZENIA")],
        features=["multiline", "labels_above_blank_paragraphs", "attachment"],
    )
    image = Image.new("RGB", (1400, 1600), "white")
    draw = ImageDraw.Draw(image)
    regular = ImageFont.truetype(str(font), 28)
    heading = ImageFont.truetype(str(font), 35)
    draw.text((65, 60), "ANKIETA SPRAWY", font=heading, fill="black")
    draw.text((65, 160), "KONTAKT", font=heading, fill="black")
    lines = ["Adres e-mail: __________________", "Telefon: __________________", "[ ] SMS", "[ ] E-mail", "[ ] Listownie", "Tryb: ( ) Zwykły ( ) Pilny"]
    for i, line in enumerate(lines):
        draw.text((65, 270 + i * 125), line, font=regular, fill="black")
    image.save(OUT / "ankieta.png")
    image.save(OUT / "ankieta.jpg", quality=76)
    expected = [
        field("Adres e-mail", "email", "KONTAKT"),
        field("Telefon", "phone", "KONTAKT"),
        field("SMS", "checkbox", "KONTAKT"),
        field("E-mail", "checkbox", "KONTAKT"),
        field("Listownie", "checkbox", "KONTAKT"),
        field("Tryb", "radio", "KONTAKT"),
    ]
    record("ankieta.png", expected, True, ["image", "checkbox_groups", "radio_group"])
    record("ankieta.jpg", expected, True, ["jpeg_compression", "checkbox_groups", "radio_group"])
    image = Image.new("RGB", (1400, 1600), "white")
    draw = ImageDraw.Draw(image)
    draw.text((65, 60), "ZGŁOSZENIE DO EWIDENCJI", font=heading, fill="black")
    draw.text((65, 160), "DANE FIRMY", font=heading, fill="black")
    items = [("Nazwa działalności", "text"), ("NIP", "nip"), ("REGON", "regon"), ("Telefon kontaktowy", "phone")]
    for i, (label, _) in enumerate(items):
        y = 300 + i * 180
        draw.text((65, y), label, font=regular, fill="black")
        draw.line((65, y + 65, 1000, y + 65), fill="black", width=2)
    degraded = ImageEnhance.Contrast(image).enhance(0.42).rotate(2, resample=Image.Resampling.BICUBIC, fillcolor="white")
    degraded.save(OUT / "ewidencja_skan.pdf", "PDF", resolution=150, quality=80)
    record("ewidencja_skan.pdf", [field(a, b, "DANE FIRMY") for a, b in items], True, ["scanned_pdf", "low_contrast", "skew", "no_colons"])
    pdf = canvas.Canvas(str(OUT / "informacja.pdf"))
    pdf.setFont("Holdout", 14)
    pdf.drawString(45, 770, "INFORMACJA DLA MIESZKAŃCÓW")
    pdf.setFont("Holdout", 10)
    for i, text in enumerate(
        [
            "Podstawa prawna: dane są przetwarzane zgodnie z ustawą.",
            "Prosimy zapoznać się z instrukcją przed złożeniem wniosku.",
            "Dokument informacyjny nie zawiera pól do wypełnienia.",
            "Kontakt z urzędem odbywa się w godzinach pracy.",
        ]
    ):
        pdf.drawString(45, 710 - i * 35, text)
    pdf.save()
    record("informacja.pdf", [], features=["no_fields", "negative_control"])
    # Independent multipage scan from the new family source; no demo reuse.
    import pypdfium2 as pdfium

    scanned = []
    with pdfium.PdfDocument(str(OUT / "rodzina.pdf")) as source:
        for i in range(len(source)):
            page = source[i]
            bitmap = page.render(scale=2)
            scanned.append(bitmap.to_pil().convert("RGB"))
            bitmap.close()
            page.close()
    scanned[0].save(OUT / "rodzina_skan.pdf", "PDF", save_all=True, append_images=scanned[1:], resolution=144, quality=90)
    record("rodzina_skan.pdf", cases[5]["fields"], True, ["multipage_scan", "repeated_fields", "boxed_inputs"])
    engine = [
        "models.py",
        "extractors.py",
        "geometry.py",
        "layout_analyzer.py",
        "field_detector.py",
        "structure_builder.py",
        "ocr.py",
        "conditions.py",
        "dictionaries.py",
        "local_ai.py",
        "pipeline.py",
    ]
    manifest = {
        "dataset": "holdout-v1",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": "Final local synthetic holdout. Engine fixed before first run. No rule tuning on results. Not external/official COI data.",
        "matching_policy": {
            "one_to_one": True,
            "same_page": True,
            "label_similarity_threshold": 0.82,
            "type_accuracy_denominator": "matched fields",
            "section_accuracy_denominator": "matched fields with section annotation",
            "ocr_coverage": "multiset source-token recall on OCR cases; expected labels/section text, no invented reference transcription",
        },
        "engine_sha256": {name: digest(ROOT / "formforge" / name) for name in engine},
        "generator_sha256": digest(Path(__file__)),
        "cases": cases,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"Frozen {len(cases)} cases; engine hashes recorded before evaluation")


if __name__ == "__main__":
    main()
