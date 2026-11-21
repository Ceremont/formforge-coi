# Remaining competition gaps after FormForge 0.3

The engine improves real extraction and passes local COI checks, but is not yet a
verified complete competition solution. Evidence and exact metric scopes are in
ENGINE_V03_REPORT.md and `evaluation/engine-v03/`.

## 1. Highest priority: semantic structure and source context

- New external form sections are not consistently recovered. GUS heading recall
  regresses despite better fields; student-form sections remain weak.
- Concatenated caption words (e.g. PESELucznia) damage labels, type inference and
  strict matching. Applicant/student/coach/representative scopes must remain distinct.
- Static fees, explanatory continuations and OCR text near blank regions can
  still become inputs. Low-confidence filtering is not a calibrated classifier.
- Merged and repeated tables are materially better, but complete row/header scope,
  person/address variants, calculated totals and units are not reliably modeled.
- Numbered source dependencies, deictic phrases, attachment alternatives, age/
  adult/minor branches and arithmetic expressions remain incomplete. Only evidenced
  supported rules are emitted; other conditions require manual confirmation.
- Whole-document splitting for bundles such as 09's three applications remains
  incomplete. Physical/logical pages are not always the correct thematic workflow.

Next acceptance gate: complete independently reviewed annotations for complex
forms, improved section/role quality and no regression in scoped field quality
on a new previously unseen corpus. Current external sample is only three forms
from two request genres, with one annotator and strict label-pattern matching.

## 2. Format completeness and runtime robustness

- Seven genuine OLE binary DOC inputs remain HTTP 415. This is a mandatory-format
  competition gap. The two newly accepted .DOC files contain verified OOXML; they
  do not establish legacy DOC support.
- Apache POI HWPF is a permissively licensed project candidate, but no converter
  has been integrated, fixture-tested, container-tested or license-audited here.
  Do not introduce GPL/AGPL tools or claim broad DOC support on this basis.
- Drawing/textbox and nested-table DOCX work, but some Word legacy blank controls,
  header/footer semantics and exact pagination still need work. Finance's subject
  field is missed. A full Word rendering/layout engine is not bundled.
- Tested large page strips work, with bounded OCR and visible source offsets.
  This does not establish arbitrary image/photo/handwriting/rotation quality.
- Hybrid PDF detection can trigger extra OCR for small embedded images, increasing
  latency. Source complexity and format variants still change recognition quality.
- Real concurrent load, peak memory and a broad Linux OCR benchmark remain needed;
  local tests alone do not establish production capacity.

Next acceptance gate: verified permissive binary-DOC conversion and a format
regression corpus with geometry/type/field-quality checks, not only HTTP success.

## 3. Native COI and submission readiness

- Actual target-platform import has not been verified. Schema/example conflicts
  (grid spelling, FINISH, defaults, validation, registry readOnly) remain documented
  implementation interpretations. All source originals are unchanged.
- Full dictionary values/versions and registry connectivity are absent. Catalog
  IDs/descriptions and initial-data mappings work locally; values are not invented.
- Dynamic requiredness lacks an official serialization contract. Explicit internal
  rules remain review items, not undocumented exported properties.
- Applicant eligibility, fees, consent text/URLs and attachment constraints require
  institution-specific confirmation. Reference policy additions remain marked.
- Local eForm preview does not reproduce all platform behavior or dynamic repeated
  row editing. It does not submit an application to an institution.
- Container execution and license/native inventory evidence must be read from the
  current Docker verification record; a full audited native SBOM remains a release
  gate even if a smoke test passes.
- A final ≤10-slide PDF presentation and ≤3-minute public demo video are submission
  deliverables, outside this engine iteration. No video is published automatically.

Next acceptance gate: native importer tests, verified dictionaries/initial data,
legal workflow review, Linux/load/security/license evidence and final defense
materials. Branch `feature/engine-upgrade` must be reviewed before any merge to main.

Research sources: [Apache POI Word/HWPF](https://poi.apache.org/components/document/index.html),
[MS-DOC binary format](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-doc/).
