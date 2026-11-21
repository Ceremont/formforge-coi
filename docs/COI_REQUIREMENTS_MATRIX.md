# Macierz wymagań COI

Wydanie 1.0. PASS oznacza wskazany kod i wykonaną kontrolę, nie sam opis funkcji.
PARTIAL nie znika po przejściu JSON Schema. Dowody finalne: pytest 196,
`evaluation/coi-final/{docker,offline}-verification.json`, `release-verification.json`,
`browser-verification.json` i 10-stronicowy PDF. SKIP źródeł w czystej paczce
jest jawny; pełny benchmark wykonano w checkout z legalnym pakietem.

Źródła: **Z** = „COI - Pełna treść zadania konkursowego.pdf”, wskazana strona
i punkt; **R** = „COI - Regulamin zadania konkursowego.pdf”, paragraf;
**T** = „Reguły techniczne konfiguracji formularzy i pól na formularzu - materiał
do zadania obligatoryjnego (2).docx”, wskazana sekcja/tabela;
**S** = „HackNation - Standardy i dobre praktyki projektowania formularzy.pdf”;
**D** = „Hacknation - Słowniki (1).docx”; **I** = „Dane inicjalne - materialy
dodatkowe do zadania rozszerzającego (2).pdf”; **J** = „OpisImportowanegoPlikuJSON
(1).docx” i niezmieniony importowanyPlikJsonSchemat (1).json.
Pełne nazwy i SHA256 oryginałów: `docs/coi-source-manifest.json`.

| ID / kategoria | Oryginalne wymaganie (fragment) | Źródło | Implementacja i kontrola | Status |
|---|---|---|---|---|
| O01 obligatory | „Usługa udostępniona przez API REST” | Z s.2, 3.2.I | `main.py` POST convert/validate; `test_api.py`, browser smoke | PASS |
| O02 obligatory | „przesłanie pojedynczego pliku będącego blankietem formularza” | Z s.4, REST API | dokładnie jeden upload; `test_api.py` | PASS |
| O03 obligatory | „PDF (.pdf)” | Z s.4, formaty | pypdf/PDFium, OCR; `test_extractors.py`, realna macierz 69 | PASS |
| O04 obligatory | „DOC (.doc .docx)” | Z s.4, formaty | `legacy_doc.py` Word97–2003 read-only i `docx_reader.py`; realne DOC/testy uszkodzeń/szyfrowania. Osadzone obiekty i starsze DOC odrzucane, brak pełnego składu Word | PARTIAL |
| O05 obligatory | „ODS (.ods)” | Z s.4 | `extractors.py`, pokryte/scalone komórki; pytest i macierz | PASS |
| O06 obligatory | „XLSX (.xlsx)” | Z s.4 | rzadkie arkusze i scalenia; `test_engine_v03.py`, macierz | PASS |
| O07 obligatory | „JPEG (.jpg .jpeg)” / „PNG (.png)” | Z s.4 | lokalny OCR, dodatkowo JPE; realne testy obrazów i limitów | PASS |
| O08 obligatory | „odpowiadającą zawartości zaimportowanego formularza” | Z s.2, 3.2.I | źródła/koordynaty/provenance; recall i sekcje niepełne, `field-metrics.json` | PARTIAL |
| O09 obligatory | „zgodną ze strukturą oczekiwaną przez aplikację” | Z s.2, 3.2.I | official adapter, modele i lokalne walidatory; pytest; konflikt schema/przykłady udokumentowany, importer niedostępny | PARTIAL |
| O10 obligatory | „Wydzielenie stron tematycznych w formularzu” | Z s.2, 3.2.I; S | `structure_builder.py`, `coi_standardizer.py`; referencje i ręcznie określony zakres oceny sekcji; nie wszystkie nowe formularze odwzorowane | PARTIAL |
| O11 obligatory | „Dokumentacja architektury rozwiązania” | Z s.2, 3.2.II | ARCHITECTURE, README, opis izolacji i przepływu; przegląd źródeł | PASS |
| Q01 supplementary | „Skorzystanie z bazy słowników, danych inicjalnych” | Z s.3, 3.3.I; D/I | katalog opisów/bindingi, wyszukiwarka, `defaultValueType` i `readOnly`; testy eksportu. Pełne wartości/rejestry niedostępne | PARTIAL |
| Q02 supplementary | „Zaproponowanie nowego słownika” | Z s.3, 3.3.II | `DictionaryMatcher`, propozycje z opcji; edytor/testy | PASS |
| Q03 supplementary | „Określenie zależności między polami, sekcjami i stronami” | Z s.3, 3.3.III | jawne reguły/COIExpression, SHOW/READ_ONLY, flow; finite-scenario refs. Numerowane i złożone reguły niepełne | PARTIAL |
| Q04 optional | „Prosty frontend umożliwiający załadowanie plików” | Z s.3, 3.3.IV | istniejący JS/Jinja, browser smoke upload/edit/export | PASS |
| Q05 optional | „Aplikacja do wizualizacji wynikowych plików json” | Z s.3, 3.3.V | lokalny eForm z modelu odwzorowywanego do COI; nie docelowy renderer | PARTIAL |
| Q06 optional | „walidacja numeru telefonu, numeru PESEL” | Z s.3, 3.3.VI | `form_validator.py`, checksum/data i typy; `test_validation.py` | PASS |
| S01 security | „weryfikacją MIME type” | Z s.4 | `FileValidator`, magic/container; `test_files.py`, błędny MIME | PASS |
| S02 security | „nie może przekraczać 250 znaków” i lista zakazanych znaków | Z s.4 | regex/limit nazwy; parametryzowane `test_files.py` | PASS |
| S03 security | „Maksymalny rozmiar ... konfigurowalny” | Z s.4–5 | settings/env + limity requestu/pliku i bramy; pytest | PASS |
| S04 security | „wyłącznie tymczasowe przetwarzanie pliku” | Z s.5 | request-scoped temp, grupy procesów/cleanup i source-page; pytest oraz realny Docker 1.0: temp directories=0 | PASS |
| S05 security | „parametrów związanych z uwierzytelnianiem JWT” | Z s.5 | HS256, secret>=32, exp/iat/sub/iss/aud, runtime env; auth testy | PASS |
| S06 security | ochrona parserów i zasobów (realizacja wymagań powyżej) | Z s.4–5 | DTD/entity/macros/ZIP bomb/path checks; time/memory/semaphore; pytest. To nie pełny pentest | PASS |
| L01 licensing | „wyłącznie rozwiązania open source, nie oparte na licencjach typu copyleft” | Z s.4 | 38 przypiętych bibliotek runtime, wybrane licencje; `runtime-licenses.json`, notices. Pełny natywny audyt obrazu osobno | PARTIAL |
| L02 licensing | „Brak użycia ... zewnętrzne API, MCP, SaaS” | Z s.4 | brak usług w runtime; realny network none PDF/DOC/OCR/model lokalny, browser external requests=[] | PASS |
| L03 licensing | „brak wymogu zakupu licencji komercyjnych” | Z s.4 | brak PyMuPDF/LibreOffice/komercyjnego modelu; dependency/license inventory | PASS |
| L04 licensing | „przysługują mu pełne autorskie prawa majątkowe do tego wkładu” | R §4.1–4.4 | istniejąca MIT zachowana, nie obejmuje materiałów organizatora. Oświadczenia zespołu i wzór umowy niezweryfikowane | UNVERIFIED |
| D01 deployment | „Python 3.14 lub nowszy” | Z s.4 | Python 3.14.5, pyproject, wykonany pytest | PASS |
| D02 deployment | „kompletną konfiguracją Docker” | Z s.5 | realne compose build/up/ps/logs, HTTP wszystkie formaty i browser E2E 1.0; Buildx Unicode obejście ASCII opisane w README | PASS |
| D03 deployment | „oficjalne obrazy bazowe”, „jawne wersjonowanie”, „nie używać tagu latest” | Z s.5 | oficjalny python:3.14.5-slim-trixie, brak latest; przegląd Dockerfile | PASS |
| D04 deployment | „dedykowanym użytkowniku ... ograniczone uprawnienia” | Z s.5 | realnie UID10001/read-only/internal/temp=0, limits i no-new-privileges; docker-verification.json | PASS |
| D05 deployment | „udostępniać wyłącznie porty wymagane” | Z s.5 | jedyny port localhost bramy; procesor internal, brak portu hosta | PASS |
| D06 deployment | „sekrety ... wyłącznie ... runtime” | Z s.5 | sekrety env runtime, JWT testy; .env/klucze/cache wykluczone przez allowlist paczki i manifest SHA | PASS |
| D07 deployment | „README.md ... budowania ... uruchomienia ... konfiguracji ... REST API” | Z s.5 | README/QUICK_START_PL: uruchomione Docker i lokalny Python, UI/API/konfiguracja/ograniczenia | PASS |
| F01 formal | „szczegółowy opis i tytuł projektu” | Z s.3, pkt 4 | README, FINAL_COMPETITION_REPORT i opis/pomiary; przegląd dokumentacji | PASS |
| F02 formal | „prezentację w formacie PDF (maksymalnie 10 slajdów)” | Z s.3, pkt 4 | docs/FormForge_COI_1.0_Presentation_PL.pdf: 10 slajdów, tekst i render zweryfikowane | PASS |
| F03 formal | „wynikowe pliki JSON” | Z s.3, pkt 4 | `evaluation/coi-final/exports`, dynamiczna konwersja i walidacja | PASS |
| F04 formal | „film ... maksymalnie 3 minuty” i dostępny link | Z s.3, pkt 4 | scenariusz będzie dostarczony; brak nagrania/publikacji | FAIL |
| F05 formal | „repozytorium kodu” | Z s.3, pkt 4 | lokalny Git; dostęp jury/URL i uprawnienia niepotwierdzone | UNVERIFIED |
| F06 formal | „na podstawie nowych plików ... podczas obrony” | Z s.6 | prospektywny R3 holdout i browser workflow; nie gwarantuje jakości dowolnego dokumentu | PARTIAL |
| T01 obligatory | „Minimum dwie strony (tabs)” | T, zasady formularza | MAIN + FINISH; `test_official_coi.py`, macierz eksportów | PASS |
| T02 obligatory | „Każda strona musi zawierać minimum jedno pole” | T, zasady formularza | adapter i business validator; empty-page testy | PASS |
| T03 obligatory | „Każde pole musi być zagnieżdżone w sekcji” | T, zasady formularza | adapter hierarchii, wyjątek INFO_SECTION FINISH; testy business | PASS |
| T04 obligatory | „Nie jest możliwe zagnieżdżenie sekcji ... w innej sekcji” | T, zasady formularza | płaska sekcja/repeating; test nested_section | PASS |
| T05 obligatory | „Na stronie końcowej nie mogą znajdować się żadne pola typu Input” | T, FINISH | wyłącznie INFO_SECTION; finish_info_only test. Referencje niepoprawiane | PASS |
| T06 obligatory | „Strony muszą być połączone ... warunkami przepływu stron” | T, zasady formularza | UUID links, reachable/forward/last FINISH; invalid_link/cycle testy | PASS |
| T07 obligatory | „atrybut obligatoryjności” / walidatory REQUIRED, EMAIL, PESEL, NIP, REGON, ZIP_CODE | T, walidatory i tabele pól | wymagane właściwości i dopuszczalne kody, source-requiredness nadal heurystyczne | PARTIAL |
| T08 obligatory | nazwy techniczne / identyfikatory / współrzędne grid | J, T, tabele komponentów | UUID5, unique techName, x/y/rows/cols; recursive/profile/business testy | PASS |
| T09 supplementary | „musi mieć zdefiniowane dynamiczne stany pola ... (jsonata)” | T, SHOW/READ_ONLY | kompilacja, parser, references/cycles; tylko obsługiwane dowiedzione warunki | PARTIAL |
| T10 supplementary | „jeżeli pole korzysta ze słownika, to tablica jest pusta” | T, SELECT/CHECKBOX/RADIO; D | dictionaryName + options=[]; tests eksportu słowników | PASS |
| T11 supplementary | dane inicjalne / rejestry | I, registry attributes; T | EXTERNAL_SYSTEM + registry.attribute/readOnly; testy serializacji, bez połączenia z rejestrem | PARTIAL |
| T12 obligatory | repetingSectionGrid / repeatingSectionGrid | J schema vs T i referencje 01/05 | jawna kompatybilność wejścia, poprawna pisownia przykładów na wyjściu; testy aliasu i rekurencji | PASS |
| T13 obligatory | rzeczywisty import do systemu docelowego | Z s.4, wynik | lokalne schema/business/reference checks rozdzielone; importer niedostępny | UNVERIFIED |

Nieocenione w pełni: zgodność prawna treści zgód, opłat i uprawnień wnioskodawcy,
wszystkie szczegółowe wytyczne językowe S oraz rzeczywiste zachowanie platformy.
Oznaczenia PASS kontroli lokalnej nie podnoszą tych pozycji do PASS.
