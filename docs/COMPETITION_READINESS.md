> Historical report from the preview phase. The current official COI implementation and verification are described in [COI_COMPATIBILITY_REPORT.md](COI_COMPATIBILITY_REPORT.md) and [REFERENCE_COMPARISON.md](REFERENCE_COMPARISON.md). Earlier missing-material and compatibility statements below are superseded.

# Competition readiness — FormForge upgrade

This extends the existing application. Baseline audit: `COI_GAP_ANALYSIS.md`.
Detailed measured quality: `ACCURACY_REPORT.md`; raw results/hashes are retained.

## P0 / P1 delivery status

| Item | Status | Evidence / material limitation |
|---|---|---|
| P0.1 official compatibility | **blocked by missing official materials**; infrastructure delivered | local mapping configuration, ConfiguredAdapter + JSON Schema, exact fixture verification script; API remains preview |
| P0.2 understanding | enhanced, not a solved general document-understanding problem | vector/raster blanks, above/left label pairing, columns, tables, repeated labels, roles, groups and provenance; holdout errors retained |
| P0.3 OCR | implemented and exercised | bounded original/contrast/deskew/scale/threshold candidates, quality scoring and coordinate restoration; text PDF avoids OCR |
| P0.4 field recognition | implemented initial coverage | NIP/REGON checksum, existing types, geometry/context/format hints, explicit uncalibrated score semantics |
| P0.5 unknown-document test | local frozen synthetic holdout delivered | 12 files, 67 annotated fields, fixed matching protocol; not external/official data |
| P0.6 DOC | **unsupported, HTTP 415** | licensing/feasibility study in DOC_RESEARCH; plausible Apache options require real implementation/audit/tests |
| P1.1 editor | implemented | add/delete/reorder, label/type/required, JSON validation, section/dictionary/group/condition editing, merge/split by group name; browser verified |
| P1.2 source review | implemented first level | side-by-side original → generated eForm; image overlay; PDF page navigation + bbox; PDF rectangle overlay still absent |
| P1.3 dictionaries/conditions | implemented internally; official semantics unverified | registry/matcher, proposed dictionaries, explicit initial_data, field/section visibility, conditional requiredness and cycle validation |
| P1.4 local AI | optional small prototype | MIT self-authored Naive Bayes block-role classifier, validated source IDs, no downloads/endpoints, deterministic fallback; no claim of LLM-level understanding or accuracy improvement |
| P1.5 performance/security | locally verified, container/concurrency not certified | original JWT/MIME/name/archive/size/time/temp protections retained; worker isolation; 3-page scan exercised |
| P1.6 demonstration | implemented | source review, corrections, regenerated model/eForm/download; original and extended browser flows pass |

## COI requirements covered

Python 3.14.5; REST single-file upload and actual dynamic JSON; tested PDF,
DOCX, XLSX, ODS, PNG and JPG/JPEG adapters; local components without external
runtime APIs; filename/MIME/content/size checks; temporary request-only source
handling; configurable JWT; explicit Docker image version/non-root/read-only
recipe; architecture, setup/API/configuration/license documentation; source
references; interactive review and eForm; internal dictionaries and explicit
conditions. This is not equivalent to fulfilling the entire official minimum.

## Final local verification

- **126 Python tests** (including the previous 110) exercise real files and the
  existing security regressions. No OCR tests skipped in the tested environment.
- Ruff checks and Compose configuration validation pass. Starlette emits one
  upstream HTTPX deprecation warning; this is not hidden or treated as a failure.
- Original browser flow and extended editor/source/AI flow pass in local Chrome:
  no uncaught JavaScript errors and no external HTTP(S) asset requests. Extended
  machine-readable evidence: `output/qa/review-verification.json`.
- 19 demo conversions re-executed; no demo output lookup is used by runtime.
- Frozen holdout: precision **100%**, recall **95.52%**, F1 **97.71%**, type and
  section accuracy **90.63% on matched fields**, internal JSON valid **12/12**.
  Explicit partial OCR token coverage is 100%; it is not transcription accuracy.
- Sequential worker median **0.1494 s**, p95 **2.5317 s** on this small local
  set; observed maximum child RSS **143.27 MB**, not concurrent aggregate memory.
- Linux address-space limits, Docker networking and actual image binary notices
  cannot be certified by macOS execution. Docker daemon remains unavailable;
  `docker compose config --quiet` passes, **build/run unverified**.
- Runtime Python closure is now **36 packages**, with the five new JSON Schema
  packages using MIT according to installed metadata. New image native audit
  remains required; existing native build precautions were retained.
- No source file is retained by new review functionality: the browser uses its
  local Blob; worker/OCR temporary paths remain inside the request scope and are
  cleaned after normal completion, error, timeout and cancellation handling.

## Critical gaps before claiming competition/production readiness

1. No actual COI schema, paired expected JSON, dictionaries/initial-data contracts
   or reference screens. Official mapping is unverified; `preview_incomplete`
   must remain visible. ConfiguredAdapter unit tests use a clearly identified
   toy schema, not a fabricated COI schema.
2. DOC is missing. Apache OpenOffice/POI are promising permissive project options;
   no safe audited/isolated integration is claimed.
3. Holdout misses and incorrect sections/types remain. The set is synthetic,
   small and shares some cross-format content; generalization to real unknown
   government forms is not established.
4. Docker build/run, full native SBOM, offline image transfer and load/concurrency
   testing remain unverified. The offline browser test is not an OS egress audit.
5. DOCX pagination is logical; complex tables, rotations beyond small deskew,
   handwriting, real photos, official workflow redesign and PDF bbox overlays
   need more work. Legal/conditional semantics beyond explicit supported syntax
   are review items. Large dictionary catalogs and complex initial-data contracts
   require additional integration testing.
6. A 3-minute Polish defense **script** is included (`DEFENSE_3MIN_PL.md`). A real
   recorded video, public repository, target-system import and final PDF deck
   have not been produced/published by this upgrade.

## Exact run commands

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.lock
# Install local Tesseract + pol/eng data separately; see README.
python -m uvicorn formforge.main:app --host 127.0.0.1 --port 8765
```

UI `http://127.0.0.1:8765/`, Swagger `/docs`. The selector chooses deterministic
or local-ai-assisted mode for that request. CLI/environment mode:

```bash
FORMFORGE_ANALYSIS_MODE=local-ai-assisted \
FORMFORGE_LOCAL_MODEL_PATH=formforge/data/block_roles.json \
python -m uvicorn formforge.main:app --host 127.0.0.1 --port 8765
```

```bash
python -m pytest -q
python -m ruff check formforge scripts tests
python scripts/evaluate_accuracy.py
docker compose config --quiet
docker compose up --build
```

Docker publishes localhost port 8000 by default and needs a running daemon.
Native setup/dependency installation and image construction may use the network;
processing does not. Optional local dictionary configuration:
`FORMFORGE_DICTIONARY_REGISTRY_PATH=config/dictionaries.example.json` (the
example is proposed, not official). In Docker, use a local container path/read-only
mount. See COI_MISSING_INPUTS before enabling any official adapter.
