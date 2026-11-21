"""Create actual synthetic inputs. This module is never imported by the pipeline."""

import json
from contextlib import closing
from pathlib import Path

from docx import Document
from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import CoveredTableCell, Table, TableCell, TableRow
from odf.text import P
from openpyxl import Workbook
from PIL import Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo_samples"

SPECS = {
    "zaswiadczenie": [
        [
            "WNIOSEK O WYDANIE ZAŚWIADCZENIA",
            "I. DANE WNIOSKODAWCY",
            "Imię i nazwisko *: ..............................",
            "PESEL *: ..............................",
            "Adres zamieszkania: ..............................",
            "Kod pocztowy: ..............................",
            "E-mail: ..............................",
            "Telefon: ..............................",
            "II. TREŚĆ WNIOSKU",
            "Uzasadnienie: ..............................",
            "Data złożenia: ..............................",
            "[ ] Wyrażam zgodę na kontakt elektroniczny",
            "Uwaga: pola oznaczone gwiazdką są obowiązkowe.",
        ]
    ],
    "zezwolenie": [
        [
            "WNIOSEK O WYDANIE ZEZWOLENIA",
            "I. DANE OSOBOWE",
            "Imię i nazwisko *: ..............................",
            "PESEL *: ..............................",
            "E-mail: ..............................",
            "II. ZAKRES ZEZWOLENIA",
            "Rodzaj zezwolenia: [ ] Jednorazowe [ ] Okresowe",
            "Tryb (wybierz): Zwykły; Przyspieszony",
            "Liczba dni: ..............................",
            "Data rozpoczęcia: ..............................",
            "Uzasadnienie: ..............................",
            "Załącznik: ..............................",
            "[ ] Potwierdzam prawdziwość danych",
        ]
    ],
    "zgloszenie": [
        [
            "FORMULARZ ZGŁOSZENIA",
            "I. DANE KONTAKTOWE",
            "Nazwa organizacji *: ..............................",
            "Imię i nazwisko: ..............................",
            "E-mail *: ..............................",
            "Telefon: ..............................",
            "Adres: ..............................",
            "Kod pocztowy: ..............................",
            "II. SZCZEGÓŁY ZGŁOSZENIA",
            "Liczba uczestników: ..............................",
            "Data wydarzenia: ..............................",
            "Opis zgłoszenia: ..............................",
        ]
    ],
    "wielostronicowy": [
        [
            "WNIOSEK O PRZYZNANIE DOFINANSOWANIA",
            "I. WNIOSKODAWCA",
            "Imię i nazwisko *: ..............................",
            "PESEL *: ..............................",
            "E-mail *: ..............................",
            "Telefon: ..............................",
            "Status: [ ] Osoba fizyczna [ ] Firma",
            "NIP: ..............................",
            "Jeżeli „Status” = „Firma”, pokaż „NIP”.",
        ],
        [
            "II. ADRES I INFORMACJE O PROJEKCIE",
            "Adres zamieszkania *: ..............................",
            "Kod pocztowy: ..............................",
            "Nazwa projektu *: ..............................",
            "Opis projektu (maks. 500 znaków): ..............................",
            "Kwota dofinansowania: ..............................",
            "Data rozpoczęcia: ..............................",
        ],
        [
            "III. ZAŁĄCZNIKI I OŚWIADCZENIA",
            "Załącznik: ..............................",
            "[ ] Potwierdzam kompletność dokumentów",
            "[ ] Wyrażam zgodę na kontakt elektroniczny",
            "Uwagi dodatkowe: ..............................",
            "Data złożenia *: ..............................",
            "Uwaga: formularz demonstracyjny. Nie stanowi oficjalnego dokumentu urzędowego.",
        ],
    ],
}


def font_path():
    candidates = [Path("/System/Library/Fonts/Supplemental/Arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
    return next((str(p) for p in candidates if p.exists()), None)


def write_pdf(path, pages):
    font = font_path()
    if font:
        pdfmetrics.registerFont(TTFont("Demo", font))
    c = canvas.Canvas(str(path), pagesize=(595, 842))
    c.setTitle(pages[0][0])
    for page_number, lines in enumerate(pages, 1):
        y = 785
        for i, line in enumerate(lines):
            c.setFont("Demo" if font else "Helvetica", 13 if i == 0 else 10)
            c.setFillColorRGB(0.12, 0.18, 0.3)
            # Synthetic source is intentionally plain and readable.
            c.drawString(45, y, line)
            y -= 43 if i == 0 else 34
        c.setFont("Demo" if font else "Helvetica", 8)
        c.setFillColorRGB(0.55, 0.6, 0.7)
        c.drawString(45, 35, f"FormForge - syntetyczny dokument demo | {page_number}/{len(pages)}")
        c.showPage()
    c.save()


def write_docx(path, pages):
    doc = Document()
    for page_index, lines in enumerate(pages):
        if page_index:
            doc.add_page_break()
        for i, line in enumerate(lines):
            if i == 0 or line.startswith(("I.", "II.", "III.")):
                doc.add_heading(line, level=0 if i == 0 and not page_index else 1)
            else:
                doc.add_paragraph(line)
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Numer sprawy:"
    table.cell(0, 1).text = ""
    doc.save(path)


def write_xlsx(path, pages):
    from openpyxl.styles import Font, PatternFill

    book = Workbook()
    book.remove(book.active)
    for i, lines in enumerate(pages):
        sheet = book.create_sheet(f"Dane {i + 1}")
        sheet.column_dimensions["A"].width = 72
        sheet.column_dimensions["B"].width = 32
        for row, line in enumerate(lines, 1):
            sheet.cell(row, 1, line)
            if row == 1 or line.startswith(("I.", "II.", "III.")):
                sheet.cell(row, 1).font = Font(bold=True, color="224488")
                sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
            else:
                sheet.cell(row, 2).fill = PatternFill("solid", fgColor="F2F5FA")
        sheet.cell(len(lines) + 2, 1, "Metadane: formuła bez wykonywania")
        sheet.cell(len(lines) + 2, 2, "=SUM(1,2)")
    book.save(path)


def write_ods(path, pages):
    doc = OpenDocumentSpreadsheet()
    for i, lines in enumerate(pages):
        table = Table(name=f"Dane {i + 1}")
        for n, line in enumerate(lines):
            row = TableRow()
            cell = TableCell(valuetype="string")
            if n == 0:
                cell.setAttribute("numbercolumnsspanned", 2)
            cell.addElement(P(text=line))
            row.addElement(cell)
            row.addElement(CoveredTableCell() if n == 0 else TableCell())
            table.addElement(row)
        doc.spreadsheet.addElement(table)
    doc.save(str(path))


def main():
    import pypdfium2 as pdfium

    OUT.mkdir(exist_ok=True)
    expected = {}
    for name, pages in SPECS.items():
        write_pdf(OUT / f"{name}.pdf", pages)
        write_docx(OUT / f"{name}.docx", pages)
        write_xlsx(OUT / f"{name}.xlsx", pages)
        write_ods(OUT / f"{name}.ods", pages)
        expected[name] = {
            "source_pages": len(pages),
            "required_labels": ["Imię i nazwisko", "PESEL"] if name != "zgloszenie" else ["Nazwa organizacji", "E-mail"],
            "expected_labels": [line.split(":", 1)[0].replace(" *", "") for page in pages for line in page if "........................" in line],
            "synthetic": True,
        }
    with pdfium.PdfDocument(str(OUT / "zaswiadczenie.pdf")) as pdf:
        with closing(pdf[0]) as page:
            bitmap = page.render(scale=2)
            image = bitmap.to_pil().copy()
            bitmap.close()
    image.save(OUT / "zaswiadczenie.png")
    image.save(OUT / "zaswiadczenie.jpg", quality=94)
    image.save(OUT / "zaswiadczenie.jpe", format="JPEG", quality=94)
    # A genuinely image-only PDF exercises fallback OCR.
    image.convert("RGB").save(OUT / "skan.pdf", "PDF", resolution=144)
    # Separate geometric checkbox fixture.
    from PIL import ImageDraw, ImageFont

    checkbox = Image.new("RGB", (1300, 420), "white")
    draw = ImageDraw.Draw(checkbox)
    font = ImageFont.truetype(font_path(), 28) if font_path() else ImageFont.load_default()
    draw.text((45, 40), "FORMULARZ ZGODY", fill="black", font=font)
    draw.rectangle((45, 150, 68, 173), outline="black", width=2)
    draw.text((90, 145), "Wyrazam zgode na kontakt elektroniczny", fill="black", font=font)
    draw.text((45, 245), "E-mail: ..............................", fill="black", font=font)
    checkbox.save(OUT / "checkbox.png")
    (OUT / "expected_fields.json").write_text(json.dumps(expected, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(list(OUT.iterdir()))} synthetic demo files")


if __name__ == "__main__":
    main()
