# Third-party notices and license decisions

Project code: existing MIT (`LICENSE`). Runtime Python dependency closure: 38 packages,
all pinned in `requirements.lock`, enumerated with installed metadata in
`docs/runtime-licenses.json`. The licenses below apply to application libraries;
this is not a claim that every operating-system utility in a Python/Debian image
has a permissive license. Preserve upstream license/notice files when distributing.

| Component | Selected license |
|---|---|
| FastAPI, Pydantic/core/settings, OpenPyXL, python-docx, PyJWT | MIT |
| Uvicorn, Starlette, pypdf, lxml, Jinja2, MarkupSafe | BSD-3-Clause |
| pypdfium2 | Apache-2.0 / BSD-3-Clause; retain bundled PDFium dependency notices |
| PDFium | BSD-style; third-party licenses are bundled by pypdfium2 |
| odfpy | **Apache-2.0 selected**, not the alternative GPL licenses |
| Pillow | MIT-CMU/HPND-family notices in distribution |
| pytesseract, Tesseract, traineddata | Apache-2.0 |
| python-multipart, OpenTelemetry API | Apache-2.0 |
| Vendored Swagger UI 5.31.0 | Apache-2.0; license and bundled third-party notices in static/vendor/swagger-ui |
| defusedxml, typing-extensions | PSF-family permissive licenses |
| Other transitive Python packages | MIT / BSD / Apache / PSF; see generated manifest |
| jsonata-python 0.7.1 | Apache-2.0; local parsing and finite-scenario evaluation, no external runtime |
| jsonschema 4.26.0, jsonschema-specifications, referencing, rpds-py, attrs | MIT; added for local schema validation |
| olefile 0.47 | BSD-2-Clause plus retained legacy PIL permissive notices; read-only OLE container access |

The optional Naive Bayes implementation, development training text and generated
`formforge/data/block_roles.json` are self-authored MIT project assets. No model
weights or OCR service are downloaded at runtime. The upgrade adds no OpenCV,
LLM endpoint or mandatory external inference dependency. Package metadata was
rechecked after locking. The V03 image was built and run; a complete audited
native OCI SBOM remains outstanding.

References checked during implementation:

Vendored Swagger dependencies retain their bundled notices. DOMPurify's
Apache-2.0 alternative is selected instead of its MPL alternative. The main
UI's own JavaScript has no external dependencies; React and other libraries
embedded inside the Swagger distribution are limited to the documentation page.

- [PyMuPDF licensing](https://pymupdf.io/licensing): AGPL or paid commercial.
  **Excluded** to meet the request. PDF extraction uses pypdf + PDFium instead.
- [pypdfium2 licensing](https://github.com/pypdfium2-team/pypdfium2#licensing):
  distribution includes PDFium and dependency notices. These remain installed in
  the runtime image; do not strip the wheel's license files.
- [odfpy source and Apache license](https://github.com/eea/odfpy): dual licensing;
  the project explicitly selects Apache-2.0.
- [Tesseract license](https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE)
  and [manual](https://tesseract-ocr.github.io/tessdoc/): Apache-2.0.
  Polish data used locally comes from `tessdata_fast` release `4.1.0`;
  the Docker image installs packaged `pol`/`eng` data at build time.
- [LibreOffice licenses](https://www.libreoffice.org/licenses/): MPL/LGPL.
  **Excluded** under the requested permissive-only policy. No verified permissive
  full Word converter is included. `legacy_doc.py` implements a bounded text subset
  of Word 97–2003 using BSD olefile, based on Microsoft MS-DOC, without running
  macros, field instructions or embedded objects. Encrypted/macro/embedded-object
  files and unsupported earlier versions are rejected. It is not a rendering
  engine. Two supplied `.DOC` files are verified OOXML packages and read as DOCX.
  OpenOffice is not claimed as supported.

## Native runtime boundary

Tesseract uses Leptonica (BSD-2-Clause), plus native codecs. PDFium and Pillow
ship native code and notices. JPEG/libjpeg-turbo, PNG, TIFF, WebP, OpenJPEG,
zlib, Brotli and related permissive components require preserving their notices.
PDFium's FreeType dependency permits the FreeType License alternative; select
that alternative rather than GPL. This manifest does not replace an image SBOM.

The initial Debian Tesseract packaging may link GCC OpenMP (`libgomp`, GPL with
GCC runtime exception). The exception does not impose application source disclosure,
but a strict policy excluding every GPL-labelled runtime requires a Tesseract
build with `OPENMP_BUILD=OFF`; the final Dockerfile therefore uses that build.
It also disables libcurl and libarchive in OCR. Source-building tools belong only
to the discarded build stage. Leptonica 1.87.0 is built with JPEG/PNG only,
without distro TIFF/JBIG: Debian's libtiff can pull in GPL-licensed JBIGkit.
See [Debian libtiff dependencies](https://packages.debian.org/trixie/libtiff6)
and [Leptonica build options](https://github.com/DanBloomberg/leptonica/blob/1.87.0/CMakeLists.txt).
Python/glibc/standard C++ runtime and Debian OS
components retain their upstream licenses; a blanket ban on copyleft OS code
would be incompatible with the requested standard Linux/Python image itself.
The V03 container build and actual PDF/DOCX/XLSX/OCR/JPE/large-image API scenarios
passed. `evaluation/engine-v03/container-ocr-linkage.txt` records the real image's
Tesseract linkage and confirms those excluded optional libraries are absent.
`container-python-inventory.json` records installed Python distributions. These
inventories are evidence, not a complete audited native SBOM.

The local Homebrew installation used for verification has its own toolchain and
optional training utilities. Those utilities (including optional text-layout
libraries) are not imported or redistributed by this repository. Local Tesseract
was tested at 5.5.4; the separate container verification passed with pinned 5.5.1.

## Development tooling

Pytest, Ruff, HTTPX and ReportLab are testing/generation dependencies and are
not installed in the product image. HTTPX's development TLS dependency Certifi
uses MPL-2.0; it is **not** in `requirements.lock` or the product runtime.
The current test environment emits a Starlette HTTPX deprecation warning; the
test client still passes. The older Python swagger-ui-bundle package was rejected
after browser verification because its UI did not support OpenAPI 3.1; it is not
in the product dependencies. Playwright/Chrome are optional external QA tools,
not product runtime dependencies. Poppler supplied by the environment may be
used to inspect documents during development; it is excluded from the product.

Rebuild installed-package manifest after updating versions:
`python scripts/lock_dependencies.py`. Review actual native and transitive
licenses again before submission; metadata alone is not a full binary audit.

## Organizer reference materials

Files under `reference/coi-official/` are user-supplied third-party organizer materials, preserved byte-for-byte for this project and evaluation. They are not relicensed under the project MIT license. Their original ownership and competition terms continue to apply. Runtime contains only the supplied schema copy; it never loads paired reference configurations. The clean 1.0 review package excludes raw reference packs and separately acquired originals. The bundled runtime schema retains organizer rights; confirm permission before wider public redistribution.

## Additional evaluation sources

The three blank government documents in `evaluation/engine-v03/new-documents/`
retain their original rights. Their primary-source URLs, acquisition timestamps
and SHA256 hashes are recorded in `manifest.json`. They are evaluation inputs,
not product templates or MIT-licensed project assets. The small ingress gateway
uses only Python's standard library and adds no third-party runtime dependency.

Final upgrade adds only olefile to the Python closure. Preserve its LICENSE.txt
and legacy PIL notices. Primary sources:
[olefile license](https://olefile.readthedocs.io/en/stable/License.html),
[Microsoft MS-DOC](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-doc/).
The specification is used for interoperability, not relicensed as project code.
Final native/license verification status is recorded in docs/LICENSE_COMPLIANCE.md;
the V03 container evidence above remains historical.
