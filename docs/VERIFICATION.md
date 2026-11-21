> Historical report from the preview phase. The current official COI implementation and verification are described in [COI_COMPATIBILITY_REPORT.md](COI_COMPATIBILITY_REPORT.md) and [REFERENCE_COMPARISON.md](REFERENCE_COMPARISON.md). Earlier missing-material and compatibility statements below are superseded.

# Verification report — 21 November 2026

**Historical baseline for the first MVP.** For the subsequent Document AI upgrade,
current tests, OCR behavior and frozen accuracy, see COMPETITION_READINESS.md
and ACCURACY_REPORT.md. The measurements below are retained as history.

## Executed environment

- macOS / Apple Silicon, CPython **3.14.5**.
- FastAPI 0.165.0, Pydantic 2.14.4; runtime versions in `requirements.lock`.
- Local Tesseract **5.5.4**, languages `pol`, `eng` and `osd`; no remote OCR.
- Product served at `http://127.0.0.1:8765/`; port 8000 was already occupied.
- No official COI form/JSON fixtures were present. The two provided requirement
  PDFs were read in full and also passed through the implemented PDF extractor:
  4/7 pages and 360/493 text rectangles respectively. These are requirements,
  not an accuracy benchmark for blank form conversion. Details:
  `source-material-check.json`.

## Automated checks

`python -m pytest -q` → **110 passed**, zero skipped in this environment.
One upstream warning: Starlette's HTTPX test-client integration is deprecated;
the pinned integration still works. No test failures are suppressed.

`python -m ruff check formforge scripts tests` → **all checks passed**.

`docker compose config --quiet` → **exit 0**.
**Docker build/run was not executed**: the installed Docker client could not
connect to its daemon (`docker.sock` did not exist). The multistage OCR build,
Linux resource settings and container network must still be verified on Docker.
No claim of a tested container is made.

Tests exercise format extraction, geometry/provenance, native PDF AcroForm,
DOCX paragraphs/tables/page breaks, XLSX metadata/formulas/scalings, actual ODS,
actual image/scanned-PDF OCR, geometric checkbox candidates, filename/MIME/type
limits, XML entity/macro/path traversal rejection, unknown documents with random
new labels, internal export, adapter isolation, model reference/cycle checks,
required/date/email/PESEL/phone/postal/numeric/length validation, real API worker
round trips, edited exports, safe HTML, exact single-file uploads, cleanup after
success/error, hard worker timeout, request size limits and JWT rejection/acceptance.

## Demonstration documents and exports

`python scripts/verify_samples.py` executed **19 conversions**: four scenarios
in PDF/DOCX/XLSX/ODS (16), plus PNG, JPG and scanned PDF. All 16 text-document
conversions contain their expected text-field labels. This checks explicitly
listed synthetic labels; it is **not** an official benchmark, a false-positive
measurement, or proof of 100% accuracy on unknown forms.

| Scenario | PDF fields | DOCX fields | XLSX fields | ODS fields |
|---|---:|---:|---:|---:|
| Wydanie zaświadczenia | 9 | 10 | 9 | 9 |
| Wydanie zezwolenia | 10 | 11 | 10 | 10 |
| Formularz zgłoszenia | 9 | 10 | 9 | 9 |
| Formularz 3-stronicowy | 17 | 18 | 18 | 18 |

DOCX includes an additional table field. Different physical/logical layouts can
produce different review candidates; counts do not imply all candidates are correct.
PNG/JPG yield 9 fields each; the compressed image-only PDF yields 5, including
PESEL. This exposes a real OCR quality limitation rather than hiding missing
fields. Source images are available for review. Machine-readable measurements:
`sample-verification.json`. Dynamically generated JSON exports:
`../output/demo_exports/`. Neither these exports nor `expected_fields.json` are
read by the product.

## Browser end to end

`scripts/ui_smoke.cjs` passed in installed Chrome via Playwright:

1. Open UI and confirm live health status.
2. Load a real DOCX demo through the conversion endpoint.
3. Edit a field label and required flag, regenerate and inspect JSON.
4. Download JSON, parse the actual download and assert the edited label and
   `official_coi=false`.
5. Submit empty eForm and see required-field errors; supply valid name/PESEL,
   submit to local validation API and see success.
6. Upload a real three-page PDF via file chooser.
7. Confirm NIP is hidden until “Firma” and hidden again for “Osoba fizyczna”.
8. Inspect all tabs; verify 390 px mobile layout without horizontal overflow.
9. Load locally vendored **Swagger UI 5.31.0** with OpenAPI 3.1 operations.

**Uncaught browser errors: 0. External HTTP(S) asset requests: 0.**
Browser routing denied requests to external origins throughout the test.
This checks application/browser behavior; it is not an OS-level egress audit.
Screenshots: `../output/qa/`. Desktop, mobile, field editor, eForm and Swagger
were visually inspected. The initial Swagger bundle incompatibility was fixed
before the successful run. Vendor asset hashes: `vendor-assets.json`.

## Acceptance and remaining limits

Backend, frontend, real upload/extraction/structure/JSON/preview/download,
error handling and pytest are verified locally. Docker is delivered but
unverified. DOC is explicitly unsupported. Official COI compatibility is
`preview_incomplete`; actual COI export and held-out benchmark remain missing.
Complex layout/OCR and DOCX legacy controls require further work. Formal contest
submission materials (slide deck, video, public code repository) are outside
this implementation request and have not been published.

Next five priorities: actual COI adapter and reference corpus; local layout/AI
assistance with held-out metrics; verified permissive DOC conversion; official
dictionaries and richer conditions; reproducible offline image, SBOM, presentation
and demonstration recording.
