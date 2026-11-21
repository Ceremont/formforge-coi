# Zgodność licencyjna — FormForge 1.0

**Stan całości: PARTIAL.** Sprawdzono 38 pozycji przypiętego runtime Python,
wybrane licencje OCR, zasoby własne i notices. Nie jest to opinia prawna ani pełny
audyt binarny obrazu OCI. Wymaganie COI „bez copyleft” wymaga wyjaśnienia granicy
systemu operacyjnego: standardowy Linux/glibc/GCC runtime zawiera licencje copyleft
z wyjątkami. Nie wolno przedstawiać całego kontenera jako wolnego od copyleft.

MIT istniejącego kodu zachowano. Prawa zespołu, zgody wszystkich współautorów,
wzór umowy przeniesienia praw i dopuszczalność publicznego udostępnienia schemy
organizatora pozostają **UNVERIFIED**. Nie wykonano publikacji repozytorium.
Oryginały organizatora i pobrane blankiety nie są w czystym ZIP.

## Biblioteki aplikacji

Źródło wersji/licencji: zainstalowane dystrybucje, lock i `runtime-licenses.json`.
PASS w tabeli dotyczy sprawdzenia zadeklarowanej licencji biblioteki, nie kompletnego
certyfikatu wszystkich jej binarnych komponentów. Przy dystrybucji zachować LICENSE/NOTICE.

| Zależność | Wersja | Wybrana licencja | Cel | Stan / ograniczenie | Źródło |
|---|---|---|---|---|---|
| annotated-doc | 0.0.7 | MIT | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/fastapi/annotated-doc) |
| annotated-types | 0.8.0 | MIT | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/annotated-types/annotated-types) |
| anyio | 4.16.0 | MIT | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/agronholm/anyio) |
| attrs | 26.1.0 | MIT | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://tidelift.com/subscription/pkg/pypi-attrs?utm_source=pypi-attrs&utm_medium=pypi) |
| click | 8.5.1 | BSD-3-Clause | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/pallets/click/) |
| defusedxml | 0.7.1 | PSFL | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/tiran/defusedxml) |
| et-xmlfile | 2.0.0 | MIT | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://foss.heptapod.net/openpyxl/et_xmlfile) |
| fastapi | 0.165.0 | MIT | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/fastapi/fastapi) |
| h11 | 0.16.0 | MIT | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/python-hyper/h11) |
| idna | 3.20 | BSD-3-Clause | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/kjd/idna) |
| jinja2 | 3.1.6 | BSD-3-Clause | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/pallets/jinja/) |
| jsonata-python | 0.7.1 | Apache License                            Version 2.0, January 2004                         http://www.apache.org/licenses/     TERMS AND CONDITIONS FOR USE, RE | Lokalna analiza JSONata | PASS metadane / zachować notices | [upstream](https://github.com/rayokota/jsonata-python) |
| jsonschema | 4.26.0 | MIT | Walidacja JSON Schema | PASS metadane / zachować notices | [upstream](https://github.com/python-jsonschema/jsonschema) |
| jsonschema-specifications | 2025.9.1 | MIT | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/python-jsonschema/jsonschema-specifications) |
| lxml | 6.1.3 | BSD-3-Clause | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/lxml/lxml) |
| markupsafe | 3.0.4 | BSD-3-Clause | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/pallets/markupsafe/) |
| odfpy | 1.4.1 | Apache-2.0 (selected from dual license) | Odczyt ODS | PASS metadane / zachować notices | [upstream](https://github.com/eea/odfpy) |
| olefile | 0.47 | BSD-2-Clause + legacy PIL notices | Odczyt kontenerów DOC | PASS metadane / zachować notices | [upstream](https://www.decalage.info/python/olefileio) |
| openpyxl | 3.1.5 | MIT | Odczyt XLSX | PASS metadane / zachować notices | [upstream](https://foss.heptapod.net/openpyxl/openpyxl) |
| opentelemetry-api | 1.45.2 | Apache-2.0 | Zależność FastAPI; brak SDK/eksportera/konfiguracji telemetrycznej | PASS metadane / zachować notices | [upstream](https://github.com/open-telemetry/opentelemetry-python/tree/main/opentelemetry-api) |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/pypa/packaging) |
| pillow | 13.0.0 | MIT-CMU | Obrazy/preprocessing OCR | PASS metadane / zachować notices | [upstream](https://python-pillow.org) |
| pydantic | 2.14.4 | MIT | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/pydantic/pydantic) |
| pydantic-core | 2.50.5 | MIT | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/pydantic) |
| pydantic-settings | 2.16.3 | MIT | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/pydantic/pydantic-settings) |
| pyjwt | 2.15.1 | MIT | Weryfikacja JWT | PASS metadane / zachować notices | [upstream](https://github.com/jpadilla/pyjwt) |
| pypdf | 7.1.1 | BSD-3-Clause | Tekst/AcroForm PDF | PASS metadane / zachować notices | [upstream](https://github.com/py-pdf/pypdf) |
| pypdfium2 | 5.15.2 | BSD-3-Clause, Apache-2.0, dependency licenses | Rasteryzacja PDF | PASS metadane / zachować notices | [upstream](https://github.com/pypdfium2-team/pypdfium2) |
| pytesseract | 0.3.13 | Apache License 2.0 | Lokalne wywołanie OCR | PASS metadane / zachować notices | [upstream](https://github.com/madmaze/pytesseract) |
| python-docx | 1.2.0 | MIT | Odczyt DOCX | PASS metadane / zachować notices | [upstream](https://github.com/python-openxml/python-docx) |
| python-dotenv | 1.2.4 | BSD-3-Clause | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/theskumar/python-dotenv) |
| python-multipart | 0.0.34 | Apache-2.0 | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/Kludex/python-multipart) |
| referencing | 0.37.0 | MIT | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/python-jsonschema/referencing) |
| rpds-py | 2026.9.1 | MIT | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/crate-py/rpds) |
| starlette | 1.10.0 | BSD-3-Clause | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/Kludex/starlette) |
| typing-extensions | 4.16.0 | PSF-2.0 | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/python/typing_extensions) |
| typing-inspection | 0.4.5 | MIT | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://github.com/pydantic/typing-inspection) |
| uvicorn | 0.54.0 | BSD-3-Clause | Biblioteka aplikacji lub zależność przechodnia | PASS metadane / zachować notices | [upstream](https://uvicorn.dev/) |

## OCR, biblioteki natywne, UI i modele

| Składnik | Wersja / zakres | Licencja / decyzja | Stan i ograniczenia | Źródło |
|---|---|---|---|---|
| Tesseract | 5.5.1 w obrazie; lokalny 5.5.4 | Apache-2.0 | PASS wybrana licencja; source-build bez OpenMP, curl, archive | [licencja wersji](https://github.com/tesseract-ocr/tesseract/blob/5.5.1/LICENSE) |
| Leptonica | 1.87.0 | BSD-2-Clause | JPEG/PNG, bez TIFF/JBIG; ldd finalnego obrazu zachowane | [upstream](https://github.com/DanBloomberg/leptonica/blob/1.87.0/leptonica-license.txt) |
| pol/eng traineddata | pakiety Debian; wersje w container-os-packages.txt | Apache-2.0 | Instalacja build-time; brak pobierania modeli runtime | [dane](https://github.com/tesseract-ocr/tessdata_fast) |
| PDFium / pypdfium2 natives | wheel 5.15.2 | BSD/Apache + zależności | PARTIAL audit: notices pozostają w wheel, FreeType wybrana FTL; pełna weryfikacja native SBOM otwarta | [licencje](https://github.com/pypdfium2-team/pypdfium2#licensing) |
| Pillow codecs / lxml | wersje wheel w lock | permissive upstream + bundled notices | PARTIAL audit komponentów natywnych; zachować pełne notices | [Pillow](https://github.com/python-pillow/Pillow/blob/main/LICENSE), [lxml](https://lxml.de/licensing.html) |
| Swagger UI | 5.31.0 | Apache-2.0 i third-party notices | Vendored LICENSE/NOTICE, DOMPurify wybrana Apache-2.0; osobna strona /docs | [upstream](https://github.com/swagger-api/swagger-ui/blob/v5.31.0/LICENSE) |
| UI, ikona SVG, gateway | kod własny | istniejąca MIT | Brak frameworka/CDN/fontów web; ikona bez cudzych znaków COI | repozytorium |
| Klasyfikator Naive Bayes | block_roles.json i własne dane | istniejąca MIT | Model lokalny, opcjonalny; brak wag LLM | local_ai.py, data/block_roles.json |
| Czcionki UI | system użytkownika | nie są redystrybuowane | CSS używa system-font stack | workspace.css |
| Font prezentacji PDF | DejaVu Sans 2.37 | Bitstream/Arev permissive | notice w docs/assets/fonts/LICENSE.txt; PDF i fonty narzędzia budującego, poza runtime | [upstream license](https://dejavu-fonts.github.io/License.html) |
| Bazowy Python / Debian | 3.14.5 slim-trixie, digest Dockerfile | PSF + licencje systemowe, w tym LGPL/GPL | PARTIAL w świetle ścisłego zakazu: wyjątki runtime nie zastępują interpretacji organizatora | /usr/share/doc/*/copyright, OS inventory |
| Dev/QA: pytest/Ruff/ReportLab/HTTPX/Chrome | requirements-dev.lock / środowisko | oddzielne licencje narzędzi | Nie w obrazie produktu; Certifi MPL-2.0 tylko dev; Chrome nie jest dołączany | notices i lock |

`odfpy` używany na alternatywie **Apache-2.0**, bez wyboru GPL.
`olefile` zachowuje BSD-2-Clause i historyczne notices PIL.
Nie używamy PyMuPDF (AGPL/komercyjna), LibreOffice, OpenOffice, zewnętrznych AI API,
MCP ani SaaS w produkcie. Narzędzia przygotowania/QA nie są runtime produktu.

## Dowody i pozostałe czynności

`container-python-inventory.json`, `container-os-packages.txt` i
`container-ocr-linkage.txt` w evaluation/coi-final dokumentują rzeczywisty obraz.
Lista pakietów to inventory, **nie kompletny SBOM z audytem każdego binarium**.
Przed oddaniem: wyjaśnić z COI dopuszczalność komponentów OS i wbudowanych notices,
sprawdzić wkłady zespołu i uprawnienie do przekazania praw. Zachować THIRD_PARTY_NOTICES.md.
Schemat i treści urzędowe zachowują prawa pierwotnych właścicieli; schemat jest
niezbędnym runtime asset dostarczonym do tego zadania, nie kodem objętym MIT projektu.
