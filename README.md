# FormForge COI

Istniejący projekt Document AI rozszerzony o **oficjalny COI FormDefinition**.
Domyślny eksport zawiera tylko `title`, `tabs`, `flow`. Własny model FormForge
pozostaje modelem edycji, a dawny JSON jest dostępny jako jawny tryb `preview`.

Adapter obsługuje MAIN/FINISH, UUID, SECTION/REPEATING_SECTION, siatkę,
typy pól COI, walidatory, opcje/słowniki, dane inicjalne, SHOW/READ_ONLY,
JSONata oraz połączenia stron. FINISH zawiera INFO_SECTION. Osobno sprawdzane są:
niezmieniona schema organizatora, rekurencyjny profil oraz reguły techniczne.
Eksport używa `repeatingSectionGrid`; wejście akceptuje również oficjalną literówkę
`repetingSectionGrid`. Oryginalne materiały pozostają niezmienione.

**Status: konfiguracje wymagające przeglądu; import w platformie COI niezweryfikowany.**
Poprawny JSON nie dowodzi pełnego odczytu dokumentu. Niezależna kontrola ujawniła
istotne braki w tabelach, checkboxach, zależnościach i długich dokumentach.
DOC jest nieobsługiwany. Nie deklarujemy gotowości konkursowej.

Aktualne raporty:

- [Analiza źródeł i sprzeczności](docs/OFFICIAL_COI_ANALYSIS.md)
- [Porównanie z wzorcami 01/05](docs/REFERENCE_COMPARISON.md)
- [Zgodność, niezależne testy i ograniczenia](docs/COI_COMPATIBILITY_REPORT.md)
- Pełne wyniki, eksporty i pomiary: `evaluation/coi-v1/`

Raporty z poprzedniej fazy preview są historyczne. Syntetyczny holdout v1
zachowuje poprzednie wyniki; nowy rozwój według materiałów COI zmienił silnik,
więc dawnych wyników nie przedstawiamy jako aktualnego niezależnego testu.

## Uruchomienie

Python 3.14 oraz Tesseract z `pol` i `eng`. Na macOS:
`brew install tesseract tesseract-lang`. Na Debian/Ubuntu:
`sudo apt-get install tesseract-ocr tesseract-ocr-pol tesseract-ocr-eng`.
Instalacja wymaga sieci; działający produkt nie korzysta z zewnętrznych AI API,
CDN, pobierania modeli ani usług OCR.

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.lock
cp .env.example .env
python -m uvicorn formforge.main:app --host 127.0.0.1 --port 8765 --no-access-log
```

UI: http://127.0.0.1:8765/ · Swagger: http://127.0.0.1:8765/docs.
Tylko runtime: `python -m pip install -r requirements.lock`.
Przykłady syntetyczne są już w `demo_samples/`.

```bash
docker compose config --quiet
docker compose up --build
```

Docker publikuje port 8000. Konfiguracja Compose jest sprawdzona, ale budowa
i uruchomienie obrazu pozostają **niesprawdzone: brak działającego daemon Docker**.
Obraz buduje Tesseract 5.5.1 i Leptonica bez problematycznych opcjonalnych zależności;
lokalne testy używały Tesseract 5.5.4. Pełny native SBOM nadal jest potrzebny.

## Praca w UI

Prześlij PDF, DOCX, XLSX, ODS, JPG/JPEG lub PNG. Analiza tworzy model edycji,
oficjalny JSON i raport. Zakładka **Zgodność z COI** pokazuje trzy walidacje,
błędy sekcji/powiązań, cechy nieobsługiwane, źródła ustaleń oraz pola wymagające
potwierdzenia. Sekcje dodawane według standardów COI mają oddzielne pochodzenie;
nie są przedstawiane jako pola odczytane z papieru.

Edytuj etykiety, typy, opcje, walidację, sekcje, grupy i kolejność. W ustawieniach
pola można zmienić właściwości COI: słownik, readOnly, binding danych inicjalnych,
drzewo warunków i potwierdzenie. Warunki sekcji są dostępne pod tabelą.
Grupę można oznaczyć jako powtarzalną; lokalny podgląd nie implementuje pełnego
cyklu dodawania/usuwania jej wierszy. Usunięcie pola sterującego wymaga najpierw
poprawienia zależności.

Po „Zastosuj zmiany” walidacja i JSON są przeliczane. Pobierany
`formforge-coi.json` jest samym FormDefinition, bez metadanych FormForge.
Brak błędów technicznych umożliwia eksport; ostrzeżenia i niepotwierdzone decyzje
nadal wymagają przeglądu przed publikacją.

Podgląd jest lokalnym przybliżeniem eForm, nie silnikiem COI. Rejestry nie są
podłączone; pola EXTERNAL_SYSTEM są zablokowane i opisane bindingiem. Pełne
wartości słowników TERYT/Kraje udostępnia platforma, nie ten pakiet. Nie ma wysyłki
do urzędu. Wpisane dane i wybrane załączniki nie są utrwalane.

## API

| Metoda i ścieżka | Znaczenie |
|---|---|
| GET `/api/health` | Python, OCR, offline, status zgodności |
| GET `/api/v1/formats` | Format/MIME i ograniczenia |
| POST `/api/v1/forms/convert` | Multipart `file`; model, surowe wykrycie, dokument, etapy, eksport i raport |
| POST `/api/v1/forms/validate` | `form`, opcjonalnie `values`, `export_format`; walidacja i ponowny eksport |
| POST `/api/v1/forms/preview` | `form`; HTML podglądu i eksport |
| GET `/api/v1/coi/schema` | Niezmieniona schema organizatora |
| POST `/api/v1/forms/coi-validate` | Surowy FormDefinition → raport zgodności |

```bash
curl -F 'file=@demo_samples/zaswiadczenie.pdf;type=application/pdf' \
  'http://127.0.0.1:8765/api/v1/forms/convert?export_format=official' > result.json
python -c 'import json; x=json.load(open("result.json")); print(json.dumps(x["export"],ensure_ascii=False,indent=2))' > formforge-coi.json
curl -H 'Content-Type: application/json' --data-binary @formforge-coi.json \
  http://127.0.0.1:8765/api/v1/forms/coi-validate
```

Wsteczna zgodność: `convert?export_format=preview`; w validate/preview JSON
`"export_format":"preview"`. Odpowiedź convert zawsze zachowuje `preview_export`.
Tryb analizy `deterministic` jest domyślny. Opcjonalny `local-ai-assisted` to mały
lokalny klasyfikator Naive Bayes, nie LLM; nie deklarujemy poprawy jakości dzięki niemu.

## Testy i odtwarzanie pomiarów

```bash
python -m pytest -q
python -m ruff check formforge scripts tests
python scripts/evaluate_coi.py references
python scripts/evaluate_coi.py independent
```

`evaluation/coi-v1/engine-freeze.json` zawiera hashe silnika sprzed niezależnego
przetwarzania 02/03/04/06/07/08/09. Polecenie `independent` odmawia działania po
zmianie silnika. Istniejącego freeze nie nadpisujemy. Dalszy rozwój wymaga nowej
wersji pomiaru i nowych, wcześniej nieoglądanych dokumentów do niezależnego testu.
`references` to zbiór rozwojowy, a nie niezależna ocena.

Opcjonalny Playwright z lokalnym Chrome:

```bash
node scripts/ui_smoke.cjs
node scripts/ui_review.cjs
node scripts/ui_coi.cjs
```

Zmienne `FORMFORGE_CHROMIUM`, `FORMFORGE_PLAYWRIGHT_MODULE`, `FORMFORGE_BASE_URL`
pozwalają wskazać istniejącą instalację. Zrzuty i wyniki: `output/qa/`.

## Bezpieczeństwo i licencje

Upload działa w krótkotrwałym procesie, z limitami, kontrolą MIME/sygnatur,
ZIP/XXE/makr, timeout i czyszczeniem katalogu żądania. Podgląd oryginału korzysta
z lokalnego Blob URL. Dostępny jest JWT HS256; konfiguracja w `.env.example`.
Nie ma bazy dokumentów ani zewnętrznej analizy. Docker ogranicza egress;
instalacja natywna korzysta z izolacji systemu gospodarza.

Kod: MIT. 37 przypiętych bibliotek runtime: `requirements.lock`,
`docs/runtime-licenses.json`, [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md).
JSONata jest wykonywana lokalnie przez Apache-2.0 `jsonata-python`.
PyMuPDF i LibreOffice nie są zależnościami. Materiały organizatorów w `reference/`
zachowują własne prawa i warunki; licencja MIT projektu nie przenosi na nie praw.
Nie zmieniono ich zawartości. Produkt nie ładuje etalonowych JSON podczas konwersji.
