"""Installed runtime metadata inventory; does not certify a native OCI SBOM."""
import importlib.metadata as metadata
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    entries = json.loads((ROOT / 'docs/runtime-licenses.json').read_text())
    rows = []
    purposes = {'olefile': 'Odczyt kontenerów DOC', 'pypdf': 'Tekst/AcroForm PDF', 'pypdfium2': 'Rasteryzacja PDF', 'pillow': 'Obrazy/preprocessing OCR', 'pytesseract': 'Lokalne wywołanie OCR', 'python-docx': 'Odczyt DOCX', 'odfpy': 'Odczyt ODS', 'openpyxl': 'Odczyt XLSX', 'pyjwt': 'Weryfikacja JWT', 'jsonata-python': 'Lokalna analiza JSONata', 'jsonschema': 'Walidacja JSON Schema', 'opentelemetry-api': 'Zależność FastAPI; brak SDK/eksportera/konfiguracji telemetrycznej'}
    for entry in entries:
        name = entry['name']
        dist = metadata.distribution(name)
        license_name = entry['license']
        if not license_name:
            license_name = ' / '.join(c.split(' :: ')[-1] for c in entry['classifiers'] if c.startswith('License ::')) or 'UNVERIFIED'
        if name == 'olefile':
            license_name = 'BSD-2-Clause + legacy PIL notices'
        urls = dist.metadata.get_all('Project-URL', [])
        source = next((v.split(',', 1)[-1].strip() for v in urls if any(k in v.lower() for k in ['source', 'repository', 'homepage'])), dist.metadata.get('Home-page') or f'https://pypi.org/project/{name}/{entry["version"]}/')
        selected = license_name.replace('\n', ' ')[:160].replace('|', '/')
        rows.append(f'| {name} | {entry["version"]} | {selected} | {purposes.get(name, "Biblioteka aplikacji lub zależność przechodnia")} | {"UNVERIFIED" if license_name == "UNVERIFIED" else "PASS metadane / zachować notices"} | [upstream]({source}) |')
    text = '''# Zgodność licencyjna — FormForge 1.0

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
''' + '\n'.join(rows) + '''

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
'''
    (ROOT / 'docs/LICENSE_COMPLIANCE.md').write_text(text)
    print(f'License metadata report: {len(rows)} runtime distributions; overall PARTIAL')


if __name__ == '__main__':
    main()
