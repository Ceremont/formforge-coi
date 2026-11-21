# FormForge COI 0.4 — Intelligence & Compliance

Offline Document AI dla istniejącego projektu HackNation 2026. Python 3.14,
FastAPI, lokalny OCR, edytor i oficjalny COI `title/tabs/flow`.

**Stan: propozycja wymagająca przeglądu; nie potwierdzono importu na platformie COI.**
Poprawny JSON nie oznacza pełnego odczytu dokumentu. UI pokazuje partial,
no_fields/review_required, źródła i reguły wymagające potwierdzenia.

Aktualne wyniki: **68/69** plików organizatorów przetworzonych (wcześniej 53/69),
68/68 lokalnie poprawne COI, **191 pytest**, zachowane wcześniejsze API/UI.
Odczyt tekstu Word 97–2003 działa; DOC z osadzonymi obiektami jest odrzucany. Trzy nowe zewnętrzne dokumenty
oceniono oddzielnie, z oznaczeniami zapisanymi przed predykcją. Dokładny zakres
metryk, słabe punkty sekcji oraz wyniki before/after:

- [FINAL_ACCURACY_REPORT](docs/FINAL_ACCURACY_REPORT.md)
- [COI_REQUIREMENTS_MATRIX](docs/COI_REQUIREMENTS_MATRIX.md)
- [ENGINE_V03_REPORT — historyczny](docs/ENGINE_V03_REPORT.md)
- [REMAINING_COMPETITION_GAPS](docs/REMAINING_COMPETITION_GAPS.md)
- [Kontrakt i sprzeczności COI](docs/OFFICIAL_COI_ANALYSIS.md)
- `evaluation/engine-v03/README.md` i pełne wyniki/eksporty

Starsze raporty opisują fazę preview/COI-v1. Zamrożone `coi-v1` i syntetyczny
holdout pozostają historycznymi wynikami; nie przedstawiamy ich jako nowego
niezależnego testu po rozwoju silnika.

## Instalacja i start natywny

Wymagane Python 3.14 oraz Tesseract z `pol` i `eng`.
macOS: `brew install tesseract tesseract-lang`.
Debian/Ubuntu: `sudo apt-get install tesseract-ocr tesseract-ocr-pol tesseract-ocr-eng`.
Instalacja wymaga sieci; działający produkt nie używa zewnętrznych AI API,
usług OCR, CDN ani pobierania modeli/słowników.

Z katalogu czystej instalacji:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.lock
cp .env.example .env
python -m uvicorn formforge.main:app --host 127.0.0.1 --port 8765 --no-access-log
```

UI: http://127.0.0.1:8765/ · Swagger: http://127.0.0.1:8765/docs.
Runtime bez narzędzi testowych: `python -m pip install -r requirements.lock`.

## Docker

Poniższy przebadany obraz opisuje etap 0.3. Nowy obraz i pełna weryfikacja
wydania nastąpią w etapie 1.0; aktualny silnik 0.4 działa natywnie.

```bash
docker build -t formforge-coi:0.3.0 .
FORMFORGE_HTTP_PORT=8766 docker compose up -d --no-build
docker compose logs --tail=30
docker compose down
```

UI kontenera: http://127.0.0.1:8766/. Domyślny port Compose to 8000;
`FORMFORGE_HTTP_PORT` pozwala uniknąć zajętego portu. Bezpośredni build omija
problem Compose Bake z przyznawaniem dostępu do ścieżki Unicode na tym hoście.
Compose config: `docker compose config --quiet`.

Obraz: `python:3.14.5-slim-trixie`; dedykowany użytkownik 10001, read-only root,
tmpfs, limity CPU/RAM/PID, brak capabilities. Procesor dokumentów ma wyłącznie
sieć `internal`; mała brama na standardowej bibliotece Python udostępnia lokalny
port i przekazuje żądania tylko do tego procesora. Oddzielna sieć wejściowa omija
ograniczenie publikacji portów Docker 29 dla sieci wyłącznie wewnętrznej.
Tesseract 5.5.1
budowany bez OpenMP/curl/archive; Leptonica z JPEG/PNG. Zależności instaluje się
podczas budowy. Aktualny stan rzeczywistego build/run:
`evaluation/engine-v03/docker-verification.json` oraz ENGINE_V03_REPORT.
Pełny natywny SBOM i testy obciążeniowe pozostają osobnym wymaganiem.

## Obsługiwane wejścia

PDF tekstowy, skanowany i mieszany; DOCX z textbox/drawing i tabelami zagnieżdżonymi;
XLSX/ODS z metadanymi scaleń; PNG/JPG/JPEG/JPE. Rozszerzenie/MIME/sygnatura i
archiwa są sprawdzane. Dwa pliki `.DOC` z materiałów są naprawdę DOCX i tak są
czytane po weryfikacji pakietu. DOC Word 97–2003: ograniczony odczyt tekstu przez BSD olefile. Szyfrowanie, makra, osadzone obiekty i starsze wersje są odrzucane; bez składu Word.

Duże skany: limit źródła 80 mln pikseli i budżet 25 mln pikseli na fragment OCR.
Pionowe pasy są dzielone bez pominiętych pikseli, z logicznymi stronami i
współrzędnymi źródła. Po wyczerpaniu budżetu OCR zachowuje wcześniejszy odczyt
z ostrzeżeniem; nie deklaruje kompletności. Granice stron wymagają sprawdzenia.
DOCX ma logiczne strony/kotwice, nie wierny skład silnika Word.

## Praca i API

Upload → odczyt → model → COI → walidacja → eForm → edycja → eksport.
Zakładka **Zgodność z COI** rozdziela schemat organizatora, rekurencyjny profil,
reguły techniczne i jakość odczytu. Pole zawiera źródło, współrzędne, metodę,
score, przyczyny i requires_review. Score nie jest skalibrowanym prawdopodobieństwem.

Edytor pozwala poprawiać pola, opcje, sekcje, grupy, słowniki i reguły. Źródła są
widoczne obok modelu; duży obraz ma poprawne przesunięcia fragmentów. Oficjalny
JSON nie zawiera metadanych FormForge. Powtarzalne sekcje są eksportowane, ale
podgląd nie implementuje pełnego dodawania/usuwania dynamicznych wierszy COI.
Rejestry nie są podłączone; EXTERNAL_SYSTEM opisuje binding, bez wymyślonych danych.

| Endpoint | Znaczenie |
|---|---|
| GET `/api/health` | wersja, OCR, limity i status zgodności |
| GET `/api/v1/formats` | MIME i obsługa formatów |
| POST `/api/v1/forms/convert` | multipart `file`; model, detected_form, dokument, eksport, jakość i raport |
| POST `/api/v1/forms/validate` | `form`, opcjonalnie `values` i `export_format`; walidacja i eksport |
| POST `/api/v1/forms/preview` | HTML podglądu i eksport modelu |
| GET `/api/v1/coi/schema` | niezmieniona schema organizatora |
| POST `/api/v1/forms/coi-validate` | surowy FormDefinition → raport |
| GET `/api/v1/dictionaries?q=Kraj` | wyszukiwanie opisów oficjalnego katalogu |

```bash
curl -F 'file=@demo_samples/zaswiadczenie.pdf;type=application/pdf' \
  http://127.0.0.1:8765/api/v1/forms/convert > result.json
python -c 'import json; x=json.load(open("result.json")); print(json.dumps(x["export"],ensure_ascii=False,indent=2))' > formforge-coi.json
```

Oficjalny eksport jest domyślny. Dawny format: `?export_format=preview`, a w
validate/preview `"export_format":"preview"`. `preview_export` jest zachowany.
`analysis_mode=local-ai-assisted` używa małego lokalnego Naive Bayes; nie LLM.
Na sprawdzonym podzbiorze nie wykazano dodatkowej poprawy F1, więc tryb pozostaje
opcjonalny. Pełne wartości słowników są rozwiązywane przez platformę COI;
lokalny katalog nie udaje kompletnego zbioru wartości.

## Testy i odtwarzanie

```bash
python -m pytest -q
python -m ruff check formforge deploy scripts tests
python scripts/evaluate_v03.py known
python scripts/evaluate_v03.py new
python scripts/score_v03.py
python scripts/report_v03.py
```

`known` oznacza development/regression. `new` wymaga niezmienionego finalnego
freeze i zapisanej przed predykcją adnotacji. Nie nadpisuj freeze dla nowych
zmian; użyj kolejnej wersji i nowych nieoglądanych formularzy. `coi-v1` chroni się
przed przeliczeniem zmienionym silnikiem. Metryki bez ground truth pozostają N/A.
Oficjalne źródła w `reference/coi-official/` są dołączone do pełnego ZIP,
ale nie są śledzone przez Git. W samym checkout trzeba osobno umieścić paczkę
organizatora; pełny zestaw pytest wymaga tej paczki.

Playwright/Chrome (opcjonalne narzędzia QA):

```bash
node scripts/ui_smoke.cjs
node scripts/ui_review.cjs
node scripts/ui_coi.cjs
node scripts/ui_large_image.cjs
```

`FORMFORGE_CHROMIUM`, `FORMFORGE_PLAYWRIGHT_MODULE`, `FORMFORGE_BASE_URL` wskazują
istniejące instalacje. Zrzuty/wyniki: `output/qa/`.

## Konfiguracja i licencje

Parametry w `.env.example`: upload, strony/bloki/komórki, pamięć, współbieżność,
timeout/OCR, budżet źródła/fragmentu obrazu, tryb analizy/eksportu, katalog i JWT.
Pliki są tymczasowe i usuwane po żądaniu; brak bazy dokumentów, logowania treści
i zewnętrznej analizy. Wybrane załączniki i wartości podglądu nie są utrwalane.
JWT HS256 jest opcjonalny lokalnie; sekret/issuer/audience podaje się w runtime.

Kod: MIT. 38 przypiętych bibliotek runtime; nowa zależność olefile 0.47 (BSD).
Zobacz `requirements.lock`, `docs/runtime-licenses.json`, THIRD_PARTY_NOTICES.md.
PyMuPDF i LibreOffice nie są zależnościami. Materiały organizatorów i zewnętrznych
instytucji zachowują własne prawa/warunki. Runtime nie czyta etalonowych JSON ani
nie pobiera dokumentów z internetu. Ta iteracja nie publikuje filmu i nie scala
zmian do main.
