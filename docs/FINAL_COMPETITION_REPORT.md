# FormForge COI 1.0 — raport końcowy

**Działające wydanie do przeglądu, z niezamkniętymi wymaganiami konkursowymi.**
Rozwinięto istniejący projekt, bez przepisywania. Gałąź `feature/competition-final`,
bez merge do main, push ani zmiany widoczności. Lokalny tag wydania: `v1.0.0`.

## Zmiany etapów

| Etap | Wynik | Commit |
|---|---|---|
| 0.4 Intelligence & Compliance | ograniczony Word97 DOC, poprawki etykiet/spacji/blank tables, narracyjne pola, diagnostyka i odrębny benchmark | `b9d723a` |
| 0.5 Professional UX | przegląd, edytor/filtry/undo/auto-validation, source PDF raster/bbox, lokalny eForm/repeating/FINISH, JSON workspace i zgłoszenia COI | `bd2d754` |
| 1.0 Competition Release | bazowy digest, realny Docker/offline, concurrency/cleanup, pomiary, polskie materiały, PDF i czysta paczka | `release: FormForge 1.0 HackNation Competition Edition` |

Zachowano 323 historyczne pliki ewaluacji i 82 materiały organizatora byte-for-byte.
Rozpoznawanie po freeze R3 nie było dalej strojone. Jedyny udokumentowany guard
mappera z `mapping-hotfix.json` usuwa wyjątek na znanym zestawie 08, nie zmienia
surowych predykcji ani eksportów R3. Oryginałów i pełnych traces nie dystrybuujemy
w czystym ZIP; pozostają w autoryzowanym checkout/history.

## Dokładność i formaty

- Źródła organizatora: **62/69 → 68/69** poprawnych lokalnie eksportów. Wszystkie
  62 wcześniejsze sukcesy zachowane. 01: 8/8, 05: 7/7; łącznie 15/15.
  Inne zestawy: **53/54** (02/03/04/06/09 po 8/8, 07 6/6, 08 7/8).
- Pozostaje DOC08 z osadzonymi obiektami, HTTP415. Makr/złośliwego kodu w nim
  nie stwierdzamy — odrzucenie wynika z nieobsługiwanego kontenera.
- Referencyjne PDF/DOCX 01/05: F1 workflow **98,04% / 97,20%**, zachowane względem 0.3;
  obejmuje jawne uzupełnienia standardu. Typy/struktura i skończone scenariusze
  warunków 100% według zdefiniowanej metody; 29/31 stanów, nie dowód dowolnego JSONata.
- Trzy dokumenty development z 0.3: micro F1 **71,64% → 87,50%**.
  R1/R2 nie są finalnym niezależnym testem; błędy i wcześniejsze freezes zachowane.
- **Prospektywny R3, 3 nowe dokumenty/2 wydawców:** precision **51,85%**, recall
  **68,29%**, F1 **58,95%** (baseline F1 52,63%); typy w dopasowanych **85,71%**.
  28/41 match, 54 predykcje. Jeden anotator, ograniczona metoda etykiet/typów;
  brak pełnego ground truth workflow/warunków. Nie jest to populacyjna trafność.

| R3 | Predykcje | Dopasowania / GT | F1 0.3 → final | Brakujące / nadmiarowe |
|---|---|---|---|---|
| residence-cert PDF | 19 | 10/14 | 60,61% → 60,61% | 4 / 9 |
| civil-record PDF | 24 | 10/15 | 35,90% → 51,28% | 5 / 14 |
| krk-company DOCX | 11 | 8/12 | 69,57% → 69,57% | 4 / 3 |

Wszystkie trzy przeszły również pełny browser workflow na finalnym Docker:
upload → rozpoznanie → źródło → ręczna korekta etykiety → preview → zgodność →
eksport. Czasy automatycznego skryptu UI 1,72/1,90/1,95 s **nie są czasem pracy
człowieka ani tylko ekstrakcji**. Korekta pierwszej etykiety testuje mechanizm
edycji; nie została użyta do poprawienia wyniku benchmarku i nie usuwa wszystkich
rzeczywistych braków. Metryki scoringu pozostają surowe.

Brakujące R3: certificate_kind, registration_stay, deregistration_stay, relationship;
copy_kind, act_kind, person1, event1, person2; requesting_org, krs, country,
proceeding. Brak wyborów z podkreśleń/skreśleń i część pól urzędowych są szczególnie
ryzykowne. Dokładne predykcje/matche: `field-metrics.json`, źródła/SHA/anotacje w manifestach.

## Zgodność COI

Macierz 53 pozycji: **37 PASS, 12 PARTIAL,
1 FAIL, 3 UNVERIFIED**. PASS ma zakres wskazanej kontroli.
Schemat/profil/reguły nie potwierdzają prawidłowości prawnej ani kompletności.

Gotowe lokalnie: title/tabs/questions/field/flow, MAIN/FINISH, UUID, sekcje,
repeating, grid, typy, walidatory, options/dictionaryName, jawne states i linki.
Świadoma obsługa repetingSectionGrid na wejściu, repeatingSectionGrid na wyjściu.
Nie poprawiano oficjalnych przykładów. FINISH naszego eksportu ma INFO_SECTION bez input.

Częściowe: DOC, kompletność/tematyczne strony nowych dokumentów, dobór słowników,
rejestry, niejawne zależności i pełna zgodność importera. Dynamiczne REQUIRED nie
ma potwierdzonego kontraktu eksportu. Brak wiarygodnego dowodu dla boolean condition
z pustymi opcjami daje warning/unsupported, nie wymyślone JSONata.
Rzeczywisty importer **UNVERIFIED**, `target_import_verified=false`.

## Wykonane kontrole

| Zakres | Faktyczny wynik |
|---|---|
| Pełny pytest w checkout z organizer pack | **196 passed**, 0 failed, 12,49 s; jedno ostrzeżenie Starlette/HTTPX dev |
| Ruff | PASS, formforge/deploy/tests/scripts |
| UI native | smoke, rozbudowany edytor, referencja05 i raster61,9MP przeszły |
| UI Docker1.0 | smoke i professional final, trzy nowe dokumenty, 1280×800/390×844; brak browser errors/external requests |
| Bezpieczeństwo | MIME/nazwa/magic/ZIP/XML/makra/corruption, JWT, timeout, ograniczenia zasobów i cleanup w pytest; dwa realne równoległe uploady oraz 429/recovery |
| Source-page | realny PNG strony, invalid page/format, JWT, jeden plik i cleanup |
| COI | adapter/schema/recursive profile/business, słowniki, stany/repeating/flow; actual importer nie |
| PDF | 10 stron, render/oględziny wszystkich, Polish glyph coverage i extractable text, font notice |

JSON validity oznacza 68/68 zaakceptowanych wyników organizatora i 3/3 R3 w lokalnych
kontrolach. Nie ukrywamy 1 odrzuconego DOC w mianowniku 69.
Testy wymagające nieobjętych prawem redystrybucji oryginałów w czystym ZIP jawnie
SKIP; wynik tej kopii: **181 passed, 15 skipped**, 1 ostrzeżenie, UI/API i konwersja z rozpakowanych źródeł przeszły. Szczegóły w `package-verification.json`.

## Docker i offline

Realnie wykonano build/up/ps/logs oraz HTTP/API/frontend. Oba serwisy zdrowe,
UID10001, read-only/tmpfs, procesor tylko internal network, po testach temp=0.
Docker Desktop 29.8.2 ARM64; base Python3.14.5 pinned SHA256 w Dockerfile.
Buildx Unicode path entitlement error obejściem: identyczny kontekst w ASCII /tmp;
nie twierdzimy, że polecenie w Unicode katalogu przeszło. Instrukcja README.

Osobny obraz `--network none`: udany HTTP PDF/DOC/PNG OCR + własny model lokalny,
zewnętrzne IP bez trasy, temp cleanup. Browser requests do zewnętrznych hostów=0.
Initial installation/build wymaga sieci; runtime nie pobiera modeli/fontów/JS.
Nie używamy usług AI API, MCP/SaaS ani telemetry exporterów w produkcie.

## Wydajność — jeden przebieg na własnych dokumentach

Python3.14.5, macOS ARM64. Osobny proces dla każdej próbki, po instalacji; nie load test.
OCR jest **częścią extraction**, nie dodatkowym czasem do zsumowania. Analysis to
suma rejestrowanych etapów poza extraction; total obejmuje również normalizację.
RSS dotyczy procesu Python/PDFium, **nie łącznego szczytu z Tesseract child**.
Brak import-time/HTTP/queue w total. Nie deklarujemy przyspieszenia.

| Próbka | Extraction s | OCR s | Analysis s | Total s | Python peak MiB |
|---|---|---|---|---|---|
| zaswiadczenie.pdf | 0.110 | 0.000 | 0.004 | 0.116 | 72.5 |
| zezwolenie.docx | 0.044 | 0.000 | 0.003 | 0.051 | 63.0 |
| zgloszenie.xlsx | 0.051 | 0.000 | 0.003 | 0.056 | 59.4 |
| zaswiadczenie.png | 1.035 | 0.965 | 0.004 | 1.041 | 93.1 |
| wielostronicowy.pdf | 0.050 | 0.000 | 0.012 | 0.064 | 74.2 |

Duży raster09: 61,9MP, 16 tiles, 181 pól, 56,46 s browser journey native, poprawny
lokalnie eksport i jawny wynik partial. To dowód obsługi limitów, nie trafności 181 pól.

## Licencje i formalności

38 runtime Python pinned; wybrane licencje i notices opisane w LICENSE_COMPLIANCE.
Tesseract bez opcjonalnych libgomp/tiff/jbig/curl/archive potwierdzony ldd.
Zachowano inventory Python/OS; to nie pełny native SBOM. Granica zakazu copyleft
wobec standardowego OS, prawa zespołu/umowa i publiczne rozpowszechnienie schemy
pozostają otwarte. Istniejąca MIT nie rozszerza się na materiały organizatora.
Czysty ZIP wyklucza raw reference pack, źródła zewnętrzne, .env/klucze/cache/venv.
Dołączone własne demo, kod, lock, runtime schema z prawami organizatora, notices,
wynikowe JSON, metryki, PDF i dokumentacja. Internet do instalacji opisany jawnie.

Film publiczny <=3 min **FAIL: brak nagrania i linku**. Dostęp jury do repo oraz
formalności prawne **UNVERIFIED**; nie zmieniano visibility ani nie wysyłano wiadomości.

## Uruchomienie i demonstracja

```sh
docker compose build
docker compose up -d --wait
curl http://127.0.0.1:8000/api/health
```

UI http://127.0.0.1:8000, Swagger /docs. Alternatywa Python3.14/Tesseract i konfiguracja
JWT w README/QUICK_START_PL. Demo 2:45: nowy dokument → źródło → korekta → eForm →
zgodność → pobranie JSON. Awaryjne scenariusze w FINAL_DEMO_PL, 31 odpowiedzi w JURY_QA_PL.

Przed konkursem trzy największe ryzyka: **nowe pola/warunki**, **rzeczywisty importer**,
**licencje/prawa/formalności**. Następny etap powinien je zamknąć; wersja1.0 nie
jest deklaracją pełnej gotowości produkcyjnej ani spełnienia całego regulaminu.
