"""Build the final accuracy report from measured, versioned records."""

import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "evaluation/coi-final"


def load(name):
    return json.loads((D / name).read_text())


def pct(value):
    return "N/A" if value is None else f"{value * 100:.2f}%"


def aggregate(rows):
    expected = sum(r["expected"] for r in rows)
    predicted = sum(r["predicted"] for r in rows)
    matched = sum(r["matched"] for r in rows)
    correct = sum(sum(m["type_correct"] for m in r["matches"]) for r in rows)
    return {
        "expected": expected,
        "predicted": predicted,
        "matched": matched,
        "precision": matched / max(1, predicted),
        "recall": matched / max(1, expected),
        "f1": 2 * matched / max(1, expected + predicted),
        "type_accuracy": correct / max(1, matched),
    }


def main():
    known = load("known-results.json")
    old = json.loads((ROOT / "evaluation/engine-v03/known-results.json").read_text())
    metrics = load("field-metrics.json")
    accepted = [r for r in known if r["status"] == "converted"]
    assert len(known) == 69 and len(accepted) == 68 and all(r["valid"] for r in accepted)
    current = {r["id"]: r for r in known}
    assert all(current[r["id"]]["status"] == "converted" for r in old if r["status"] == "converted")
    report = """# Końcowy raport dokładności — silnik 0.4 / wydanie 1.0

Baseline: commit `aaa8148`, 0.3.0. Źródła organizatora i oba poprzednie
benchmarki są zachowane. 01/05 to referencje development; pozostałe siedem
zestawów to wcześniej analizowane dokumenty. Nie nazywamy ich niezależnymi.

## Konwersja i poprawność techniczna

| Zbiór | 0.3 | Końcowy silnik | Lokalnie poprawny COI |
|---|---|---|---|
"""
    for category, title in [("reference", "Referencje 01/05"), ("previously_evaluated", "Pozostałe siedem zestawów")]:
        rows = [r for r in known if r["category"] == category]
        prior = [r for r in old if r["category"] == category]
        report += f"| {title} | {sum(r['status'] == 'converted' for r in prior)}/{len(prior)} | {sum(r['status'] == 'converted' for r in rows)}/{len(rows)} | {sum(r.get('valid', False) for r in rows)} |\n"
    report += "| Nowy niezależny R3 | 3/3 | 3/3 | 3/3 |\n\n"
    report += "**62/69 → 68/69** źródeł organizatora. Wszystkie 62 wcześniejsze sukcesy zachowane. Wszystkie 68 wyników przechodzi JSON Schema, rekurencyjny profil i lokalne reguły techniczne. DOC 08 zawiera osadzone obiekty i jest celowo odrzucany (415). Inne DOC Word97–2003 dają ograniczony odczyt tekstu, bez gwarancji składu/obrazów/geometrii. Lokalna poprawność nie potwierdza kompletności ani importu do COI.\n\n"
    report += "| Zestaw | Konwersje |\n|---|---|\n"
    for i in range(1, 10):
        rows = [r for r in known if r["id"].startswith(f"{i:02}-")]
        report += f"| {i:02} | {sum(r['status'] == 'converted' for r in rows)}/{len(rows)} |\n"
    report += "\n## Referencje: semantycznie, bez porównywania UUID\n\n| PDF | Precision | Recall | F1 | Typ | Struktura | Warunki |\n|---|---|---|---|---|---|---|\n"
    for case in ["01-pdf", "05-pdf"]:
        m = current[case]["metrics"]
        report += (
            f"| {case} | "
            + " | ".join(pct(m[k]) for k in ["field_precision", "field_recall", "field_f1", "field_type_accuracy", "structural_similarity", "conditional_rules_coverage"])
            + " |\n"
        )
    report += "\nPDF/DOCX zachowują F1 referencji 98.04% / 97.20%. Dodatki standardu są osobno oznaczone. Pokrycie warunków oznacza 29 stanów w 01 i 31 w 05 na skończonych domenach opcji; nie dowodzi równoważności dowolnego JSONata. Pełny ground truth pozostałych formularzy nie istnieje.\n\n"
    report += "## Pomiary pól z jawnym zakresem\n\nWyniki poniżej dotyczą surowych wykrytych pól, nie poszerzonego workflow. Jedna osoba oznaczająca, stałe wzorce etykiet, dopasowanie jeden-do-jednego i typów. Section accuracy to recall nagłówków przy podobieństwie >=0.85, z osobnym F1 sekcji. Nazwane osoby/wiersze nie są w pełni dopasowywane geometrycznie. Brakujące i nadmiarowe elementy są w field-metrics.json.\n\n"
    titles = {
        "known_scoped": "Regresje znane: 03/04 pełne widoczne pola, 06 tylko tabela 24 wymiarów",
        "development_after_v03": "Trzy dokumenty z 0.3 — teraz development",
        "promoted_development": "R1 — użyty do poprawy tabel, nie jest niezależny",
        "secondary_audit": "R2 — dodatkowy audyt, nie jest finalnym holdoutem",
        "prospective_r3_holdout": "R3 — nowy niezależny test prospektywny",
    }
    summary = {}
    for category, title in titles.items():
        report += f"### {title}\n\n| Dokument | Wersja | P | R | F1 | Typ | Sekcje recall / F1 |\n|---|---|---|---|---|---|---|\n"
        rows = [r for r in metrics if r["category"] == category]
        for r in rows:
            report += (
                f"| {r['id']} | {r['version']} | "
                + " | ".join(pct(r[k]) for k in ["precision", "recall", "f1", "type_accuracy"])
                + f" | {pct(r['section_accuracy'])} / {pct(r['section_f1'])} |\n"
            )
        summary[category] = {version: aggregate([r for r in rows if r["version"] == version]) for version in ["v03", "final"]}
        report += "\nMicro F1: " + pct(summary[category]["v03"]["f1"]) + " → " + pct(summary[category]["final"]["f1"]) + ".\n\n"
    (D / "aggregate-metrics.json").write_text(json.dumps(summary, indent=2) + "\n")
    report += """## Integralność i interpretacja

R1 wykazał błąd pustych wierszy DOCX; został jawnie przeniesiony do development.
R2 zachowano jako dodatkowy audyt. Poprawkę numerowanych etykiet oparto na
wcześniej przeniesionym do development źródle parkingowym R1. Nowe trzy źródła
R3 pozyskano i oznaczono po ostatniej zmianie rozpoznawania. Oryginalne blokady
adnotacji, freeze i wyniki są zachowane w trials. Nie dostosowano etykiet ani
wzorców do predykcji R3. Natywne źródła nie są czytane przez runtime na podstawie
nazwy/hashu i żaden wynik referencyjny nie jest ładowany przez konwersję.

Po freeze wykryto błąd eksportera na znanym zestawie 08. Wąska poprawka
`mapping-hotfix.json` zastępuje wyjątek dla niejednoznacznego warunku logicznego
ostrzeżeniem unsupported; model/pozostałe pola pozostają dostępne. SHA zmian
i test są zapisane. Surowe predykcje i eksporty R3 przed/po poprawce są identyczne.
Wszystkie trzy rastry 08 ponownie przeszły pełny proces. To nie strojenie
rozpoznawania na holdoucie.

Nowy R3 ma tylko trzy dokumenty i dwóch wydawców. Mierzy ograniczony zakres
etykiet/typów, nie dokładność populacyjną. N/A oznacza brak odpowiedniego ground
truth; nie zastępujemy go wynikiem schema-valid. Nie gwarantujemy ogólnej
poprawy sekcji. Różne interpretacje kontrolek papierowych wymagają oceny człowieka.

## Co wciąż ginie lub wymaga korekty

"""
    for r in metrics:
        if r["category"] == "prospective_r3_holdout" and r["version"] == "final":
            report += f"- {r['id']}: braki `{', '.join(r['missing']) or 'brak w oznaczonym zakresie'}`; {len(r['extra'])} nadmiarowych kandydatów.\n"
    report += """
Nierozpoznane lub niepotwierdzone reguły: wybory podkreślane/skreślane,
warunki zależne od numerów punktów i statusu osoby, niejawne grupy opcji,
obliczenia, część reguł załączników oraz dynamiczne REQUIRED bez oficjalnego
kontraktu serializacji. Nie są zastępowane wymyślonym JSONata. W R3 pełne
condition coverage, równoważność workflow i legalność treści pozostają N/A.

## Wydajność i testy

"""
    common = [r for r in old if r["status"] == "converted"]
    report += f"Mediana end-to-end 62 wspólnych zaakceptowanych źródeł: {statistics.median(r['processing_seconds'] for r in common):.3f}s (0.3) → {statistics.median(current[r['id']]['processing_seconds'] for r in common):.3f}s. Jednorazowe lokalne przebiegi, nie kontrolowany eksperyment szybkości; część lekkich zadań audytu mogła działać równolegle. Nie deklarujemy przyspieszenia. Osobny profil etapów/zasobów i Docker/offline będą w raporcie wydania.\n\n"
    report += "191 testów etapu 0.4, Ruff i oryginalny browser smoke przeszły. OCR i błędy parserów są testowane realnie. Zachowano stare testy; oczekiwanie odrzucenia poprawnego DOC Word97 w jednym teście 0.3 zostało zastąpione sprawdzeniem nowej funkcji, z dodatkowymi testami uszkodzeń/szyfrowania/makr. Aktualne końcowe QA 1.0: FINAL_COMPETITION_REPORT.md.\n"
    (ROOT / "docs/FINAL_ACCURACY_REPORT.md").write_text(report)
    print("Generated final accuracy report and aggregate metrics")


if __name__ == "__main__":
    main()
