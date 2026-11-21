# Końcowy raport dokładności — silnik 0.4 / wydanie 1.0

Baseline: commit `aaa8148`, 0.3.0. Źródła organizatora i oba poprzednie
benchmarki są zachowane. 01/05 to referencje development; pozostałe siedem
zestawów to wcześniej analizowane dokumenty. Nie nazywamy ich niezależnymi.

## Konwersja i poprawność techniczna

| Zbiór | 0.3 | Końcowy silnik | Lokalnie poprawny COI |
|---|---|---|---|
| Referencje 01/05 | 14/15 | 15/15 | 15 |
| Pozostałe siedem zestawów | 48/54 | 53/54 | 53 |
| Nowy niezależny R3 | 3/3 | 3/3 | 3/3 |

**62/69 → 68/69** źródeł organizatora. Wszystkie 62 wcześniejsze sukcesy zachowane. Wszystkie 68 wyników przechodzi JSON Schema, rekurencyjny profil i lokalne reguły techniczne. DOC 08 zawiera osadzone obiekty i jest celowo odrzucany (415). Inne DOC Word97–2003 dają ograniczony odczyt tekstu, bez gwarancji składu/obrazów/geometrii. Lokalna poprawność nie potwierdza kompletności ani importu do COI.

| Zestaw | Konwersje |
|---|---|
| 01 | 8/8 |
| 02 | 8/8 |
| 03 | 8/8 |
| 04 | 8/8 |
| 05 | 7/7 |
| 06 | 8/8 |
| 07 | 6/6 |
| 08 | 7/8 |
| 09 | 8/8 |

## Referencje: semantycznie, bez porównywania UUID

| PDF | Precision | Recall | F1 | Typ | Struktura | Warunki |
|---|---|---|---|---|---|---|
| 01-pdf | 96.15% | 100.00% | 98.04% | 100.00% | 100.00% | 100.00% |
| 05-pdf | 94.55% | 100.00% | 97.20% | 100.00% | 100.00% | 100.00% |

PDF/DOCX zachowują F1 referencji 98.04% / 97.20%. Dodatki standardu są osobno oznaczone. Pokrycie warunków oznacza 29 stanów w 01 i 31 w 05 na skończonych domenach opcji; nie dowodzi równoważności dowolnego JSONata. Pełny ground truth pozostałych formularzy nie istnieje.

## Pomiary pól z jawnym zakresem

Wyniki poniżej dotyczą surowych wykrytych pól, nie poszerzonego workflow. Jedna osoba oznaczająca, stałe wzorce etykiet, dopasowanie jeden-do-jednego i typów. Section accuracy to recall nagłówków przy podobieństwie >=0.85, z osobnym F1 sekcji. Nazwane osoby/wiersze nie są w pełni dopasowywane geometrycznie. Brakujące i nadmiarowe elementy są w field-metrics.json.

### Regresje znane: 03/04 pełne widoczne pola, 06 tylko tabela 24 wymiarów

| Dokument | Wersja | P | R | F1 | Typ | Sekcje recall / F1 |
|---|---|---|---|---|---|---|
| 03-pdf | v03 | 100.00% | 100.00% | 100.00% | 100.00% | N/A / N/A |
| 03-pdf | final | 100.00% | 100.00% | 100.00% | 100.00% | N/A / N/A |
| 04-pdf | v03 | 100.00% | 90.00% | 94.74% | 100.00% | N/A / N/A |
| 04-pdf | final | 100.00% | 90.00% | 94.74% | 100.00% | N/A / N/A |
| 06-pdf | v03 | 100.00% | 100.00% | 100.00% | 100.00% | N/A / N/A |
| 06-pdf | final | 100.00% | 100.00% | 100.00% | 100.00% | N/A / N/A |

Micro F1: 98.88% → 98.88%.

### Trzy dokumenty z 0.3 — teraz development

| Dokument | Wersja | P | R | F1 | Typ | Sekcje recall / F1 |
|---|---|---|---|---|---|---|
| new-gus-info | v03 | 73.33% | 73.33% | 73.33% | 90.91% | 0.00% / 0.00% |
| new-gus-info | final | 78.57% | 73.33% | 75.86% | 100.00% | 100.00% / 80.00% |
| new-student-card | v03 | 36.36% | 57.14% | 44.44% | 75.00% | 0.00% / 0.00% |
| new-student-card | final | 87.50% | 100.00% | 93.33% | 100.00% | 50.00% / 40.00% |
| new-finance-info | v03 | 100.00% | 90.00% | 94.74% | 88.89% | 100.00% / 88.89% |
| new-finance-info | final | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% / 88.89% |

Micro F1: 71.64% → 87.50%.

### R1 — użyty do poprawy tabel, nie jest niezależny

| Dokument | Wersja | P | R | F1 | Typ | Sekcje recall / F1 |
|---|---|---|---|---|---|---|
| final-name-change | v03 | 59.09% | 52.00% | 55.32% | 23.08% | 25.00% / 25.00% |
| final-name-change | final | 59.09% | 52.00% | 55.32% | 23.08% | 25.00% / 25.00% |
| final-parking-card | v03 | 44.00% | 44.90% | 44.44% | 54.55% | 100.00% / 16.39% |
| final-parking-card | final | 51.72% | 61.22% | 56.07% | 66.67% | 100.00% / 23.26% |
| final-tree-removal | v03 | 0.00% | 0.00% | 0.00% | 0.00% | N/A / N/A |
| final-tree-removal | final | 97.50% | 97.50% | 97.50% | 100.00% | N/A / N/A |

Micro F1: 37.43% → 70.09%.

### R2 — dodatkowy audyt, nie jest finalnym holdoutem

| Dokument | Wersja | P | R | F1 | Typ | Sekcje recall / F1 |
|---|---|---|---|---|---|---|
| final-krk-language | v03 | 83.33% | 83.33% | 83.33% | 100.00% | 0.00% / 0.00% |
| final-krk-language | final | 85.71% | 100.00% | 92.31% | 83.33% | 0.00% / 0.00% |
| final-fishing-card | v03 | 50.00% | 80.00% | 61.54% | 75.00% | N/A / N/A |
| final-fishing-card | final | 57.14% | 80.00% | 66.67% | 75.00% | N/A / N/A |
| final-pesel-request | v03 | 60.98% | 48.08% | 53.76% | 76.00% | 50.00% / 25.00% |
| final-pesel-request | final | 62.50% | 48.08% | 54.35% | 76.00% | 75.00% / 33.33% |

Micro F1: 57.63% → 59.83%.

### R3 — nowy niezależny test prospektywny

| Dokument | Wersja | P | R | F1 | Typ | Sekcje recall / F1 |
|---|---|---|---|---|---|---|
| final-residence-cert | v03 | 52.63% | 71.43% | 60.61% | 90.00% | N/A / N/A |
| final-residence-cert | final | 52.63% | 71.43% | 60.61% | 90.00% | N/A / N/A |
| final-civil-record | v03 | 29.17% | 46.67% | 35.90% | 71.43% | N/A / N/A |
| final-civil-record | final | 41.67% | 66.67% | 51.28% | 80.00% | N/A / N/A |
| final-krk-company | v03 | 72.73% | 66.67% | 69.57% | 87.50% | 20.00% / 20.00% |
| final-krk-company | final | 72.73% | 66.67% | 69.57% | 87.50% | 20.00% / 20.00% |

Micro F1: 52.63% → 58.95%.

## Integralność i interpretacja

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

- final-residence-cert: braki `certificate_kind, registration_stay, deregistration_stay, relationship`; 9 nadmiarowych kandydatów.
- final-civil-record: braki `copy_kind, act_kind, person1, event1, person2`; 14 nadmiarowych kandydatów.
- final-krk-company: braki `requesting_org, krs, country, proceeding`; 3 nadmiarowych kandydatów.

Nierozpoznane lub niepotwierdzone reguły: wybory podkreślane/skreślane,
warunki zależne od numerów punktów i statusu osoby, niejawne grupy opcji,
obliczenia, część reguł załączników oraz dynamiczne REQUIRED bez oficjalnego
kontraktu serializacji. Nie są zastępowane wymyślonym JSONata. W R3 pełne
condition coverage, równoważność workflow i legalność treści pozostają N/A.

## Wydajność i testy

Mediana end-to-end 62 wspólnych zaakceptowanych źródeł: 0.671s (0.3) → 0.589s. Jednorazowe lokalne przebiegi, nie kontrolowany eksperyment szybkości; część lekkich zadań audytu mogła działać równolegle. Nie deklarujemy przyspieszenia. Osobny profil etapów/zasobów i Docker/offline będą w raporcie wydania.

191 testów etapu 0.4, Ruff i oryginalny browser smoke przeszły. OCR i błędy parserów są testowane realnie. Zachowano stare testy; oczekiwanie odrzucenia poprawnego DOC Word97 w jednym teście 0.3 zostało zastąpione sprawdzeniem nowej funkcji, z dodatkowymi testami uszkodzeń/szyfrowania/makr. Aktualne końcowe QA 1.0: FINAL_COMPETITION_REPORT.md.
