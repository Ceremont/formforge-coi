"""Create a ten-slide Polish PDF from measured release facts, using local assets."""

from pathlib import Path
import json
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[1]
SLIDES = [
    (
        "FormForge",
        "Od dokumentu do e-formularza.",
        ["Lokalna cyfryzacja pustych blankietów urzędowych.", "Wydanie 1.0 · HackNation 2026 · niezależny projekt COI.", "Człowiek weryfikuje wynik przed eksportem."],
    ),
    (
        "Problem",
        "Blankiet jest czytelny dla człowieka. System potrzebuje struktury.",
        [
            "PDF, Word, arkusze i skany opisują te same dane w różnych układach.",
            "Sama ekstrakcja tekstu nie wystarcza do pól, typów i zależności.",
            "Poprawny JSON nie dowodzi kompletnego rozpoznania dokumentu.",
        ],
    ),
    (
        "Nasze rozwiązanie",
        "Jeden proces, z widocznymi decyzjami.",
        ["Prześlij dokument → rozpoznaj pola → porównaj ze źródłem.", "Popraw etykiety, typy, sekcje, opcje i reguły.", "Sprawdź lokalne kontrole i pobierz COI FormDefinition."],
    ),
    (
        "Jak działa system",
        "Model pośredni łączy dokument i konfigurację.",
        [
            "Czytniki formatów / OCR → analiza układu i ról bloków.",
            "Pola ze źródłami → sekcje i jawne polityki standardu.",
            "Adapter COI → schema + profil rekurencyjny + reguły techniczne.",
        ],
    ),
    (
        "Document Intelligence",
        "Dowód źródłowy zamiast niejawnej odpowiedzi.",
        [
            "Geometria PDF/obrazu, komórki arkusza i odtworzony tekst DOCX.",
            "Reguły semantyczne, lokalny Tesseract oraz opcjonalny własny Naive Bayes.",
            "Wynik heurystyki nie jest skalibrowanym prawdopodobieństwem.",
        ],
    ),
    (
        "Zgodność z COI",
        "Oficjalna struktura. Oddzielne poziomy weryfikacji.",
        [
            "MAIN / FINISH, sekcje, repeating grid, UUID, walidatory i flow.links.",
            "Słowniki, EXTERNAL_SYSTEM i ograniczone SHOW / READ_ONLY / JSONata.",
            "Rzeczywisty importer niezweryfikowany; dynamiczne REQUIRED i pełne rejestry pozostają otwarte.",
        ],
    ),
    (
        "Bezpieczeństwo i lokalność",
        "Dokument pozostaje na wskazanym serwerze.",
        [
            "Limity pliku, MIME i container checks, procesy z timeout, tymczasowe dane.",
            "Compose: UID10001, read-only, internal processor, CPU/RAM/PID limits.",
            "Realny test --network none: PDF + DOC + OCR + model lokalny. Build wymaga sieci.",
        ],
    ),
    (
        "Wyniki testów",
        "Mierzymy osobno konwersję i rozpoznanie.",
        [
            "196 pytest PASS. Browser E2E i Docker/offline sprawdzone.",
            "Źródła organizatora: 62/69 → 68/69 lokalnie poprawnych eksportów.",
            "Nowe 3 dokumenty R3: F1 pól 52,63% → 58,95%; 28/41 match, 54 predykcje. Mała próba, jeden anotator.",
        ],
    ),
    (
        "Potencjał wdrożenia",
        "Następny krok: potwierdzona integracja.",
        [
            "Test rzeczywistego importera i szerszy niezależny korpus z wieloma anotatorami.",
            "Pełne wartości słowników/rejestry, lepsze pola i złożone zależności.",
            "Audyt natywnych licencji, praw zespołu i bezpieczeństwa; bez obietnic oszczędności.",
        ],
    ),
    (
        "Przegląd, korekta, eksport",
        "Od dokumentu do e-formularza — z kontrolą człowieka.",
        [
            "Działający lokalny produkt: upload, źródło, edytor, eForm, walidacja i JSON.",
            "Referencje 01/05: F1 workflow 98,04% / 97,20%, z jawnymi dodatkami standardu; to nie holdout.",
            "Przed oddaniem: importer, formalności/licencje, dostęp jury i publiczny film ≤3 min.",
        ],
    ),
]


def main():
    fonts = ROOT / "docs/assets/fonts"
    for name, filename in [("Vera", "DejaVuSans.ttf"), ("VeraBold", "DejaVuSans-Bold.ttf")]:
        pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))
    for font in ["Vera", "VeraBold"]:
        assert all(ord(c) in pdfmetrics.getFont(font).face.charToGlyph for c in "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ→≤")
    target = ROOT / "docs/FormForge_COI_1.0_Presentation_PL.pdf"
    pdf = canvas.Canvas(str(target), pagesize=(960, 540), pageCompression=1)
    pdf.setTitle("FormForge COI 1.0 — Od dokumentu do e-formularza")
    pdf.setAuthor("FormForge project")
    pdf.setSubject("HackNation 2026: measured outcomes and remaining limitations")
    md = ["# FormForge — prezentacja PL (10 slajdów)", "", "Wersja PDF: FormForge_COI_1.0_Presentation_PL.pdf. Dane mają jawny zakres; importer pozostaje niezweryfikowany.", ""]
    for index, (title, subtitle, points) in enumerate(SLIDES, 1):
        cover = index in [1, 10]
        bg, fg, muted = ("#142a48", "#ffffff", "#c4d3e8") if cover else ("#f6f8fc", "#182c47", "#52627a")
        pdf.setFillColor(colors.HexColor(bg))
        pdf.rect(0, 0, 960, 540, fill=1, stroke=0)
        pdf.setFillColor(colors.HexColor("#4c8fe6"))
        pdf.roundRect(50, 473, 34, 34, 7, fill=1, stroke=0)
        pdf.setFillColor(colors.white)
        pdf.setFont("VeraBold", 20)
        pdf.drawString(61, 482, "F")
        pdf.setFillColor(colors.HexColor(muted))
        pdf.setFont("Vera", 10)
        pdf.drawString(98, 486, "FORMFORGE / COI 1.0")
        pdf.setFillColor(colors.HexColor(fg))
        pdf.setFont("VeraBold", 38 if cover else 30)
        pdf.drawString(50, 417, title)
        style = ParagraphStyle("subtitle", fontName="VeraBold", fontSize=23 if cover else 20, leading=29, textColor=colors.HexColor(fg))
        para = Paragraph(subtitle, style)
        _, height = para.wrap(830, 100)
        para.drawOn(pdf, 50, 374 - height + 22)
        top = 285
        body = ParagraphStyle("point", fontName="Vera", fontSize=16, leading=24, textColor=colors.HexColor(fg))
        for point in points:
            p = Paragraph(point, body)
            _, h = p.wrap(800, 100)
            pdf.setFillColor(colors.HexColor("#4c8fe6"))
            pdf.circle(57, top - 9, 3, fill=1, stroke=0)
            p.drawOn(pdf, 76, top - h + 6)
            top -= max(h + 25, 55)
        pdf.setStrokeColor(colors.HexColor("#365071" if cover else "#d7e1ee"))
        pdf.line(50, 55, 910, 55)
        pdf.setFillColor(colors.HexColor(muted))
        pdf.setFont("Vera", 9)
        pdf.drawString(50, 34, "Dowody: FINAL_ACCURACY_REPORT · COI_REQUIREMENTS_MATRIX · LICENSE_COMPLIANCE")
        pdf.drawRightString(910, 34, f"{index:02d} / 10")
        pdf.showPage()
        md += [
            f"## {index}. {title}",
            "",
            subtitle,
            "",
            *["- " + point for point in points],
            "",
            "Notatka prowadzącego: pokaż kod lub wynik kontroli; nie przedstawiaj lokalnego PASS jako importu COI.",
            "",
        ]
    pdf.save()
    (ROOT / "docs/PRESENTATION_PL.md").write_text("\n".join(md))
    from pypdf import PdfReader

    reader = PdfReader(target)
    assert len(reader.pages) == 10
    for page, (_, subtitle, _) in zip(reader.pages, SLIDES, strict=True):
        assert len(page.extract_text()) > 100
        assert "FormForge" in page.extract_text() or "FORMFORGE" in page.extract_text()
    (ROOT / "evaluation/coi-final/presentation-verification.json").write_text(
        json.dumps(dict(pages=10, text_extractable=True, embedded_font="DejaVu Sans; Bitstream/Arev permissive notices retained", visual_qa="pending"), indent=2) + "\n"
    )
    print(target)


if __name__ == "__main__":
    main()
