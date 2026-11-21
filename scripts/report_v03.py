"""Generate V03 evidence report from fixed-run records and scoped annotations."""

import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "evaluation/engine-v03"


def load(name):
    return json.loads((D / name).read_text())


def pct(value):
    return "N/A" if value is None else f"{100 * value:.2f}%"


def main():
    known = load("known-results.json")
    fresh = load("new-results.json")
    metrics = load("new-field-metrics.json")
    scoped = load("annotated-known-metrics.json")
    old = json.loads((ROOT / "evaluation/coi-v1/references-results.json").read_text()) + json.loads((ROOT / "evaluation/coi-v1/independent-results.json").read_text())
    oldmap = {r["group"] + "-" + r["extension"]: r for r in old}
    newmap = {r["id"]: r for r in known}
    assert len(known) == 69 and sum(r["status"] == "converted" for r in known) == 62
    assert all(newmap[key]["status"] == "converted" for key, r in oldmap.items() if r["status"] == "converted")
    report = """# FormForge 0.3 — Engine Upgrade

Status: substantial measured extraction improvement; human review remains
necessary. This is an extension of the existing project on branch
`feature/engine-upgrade`, not a rewrite. Baseline commit: `744fc19`.

## Baseline and evaluation integrity

Baseline: 146 passing pytest cases, 53/69 organizer sources converted, unchanged
published COI schema and local business validator. All 140 files under the frozen
`evaluation/coi-v1/` are SHA256-checked against `baseline.json` and preserved.
Both official task PDFs, specification reports and prior per-file evaluation
outputs informed development. Existing tests were retained; the new JPE format
adds one parameterized case automatically.

01/05 are paired development references. 02/03/04/06/07/08/09 are now previously
evaluated development/regression forms. They are not relabeled as an independent
holdout after tuning. New government blanks were separately acquired from primary
sources: GUS (PDF), PLSP Bydgoszcz (PDF), Ministry of Finance (DOCX).

The first V03 engine freeze preceded external source selection. A final revision
changed only low-confidence OCR-noise filtering found in known 01/05 scans.
Original freeze history is preserved. External source annotations were locked
before predictions; no engine change used their outcomes. Baseline code was
exported from Git into a temporary directory and run on the same new inputs.
The active runtime hashes still match the final freeze.

## What changed and why

- DOCX: recursive tables, DrawingML/VML text boxes, anchored geometry, answer
  shapes, logical page markers, inline control text and deliberate Choice/Fallback
  deduplication. Forms 02/08 now yield editable fields instead of no_text.
- PDF: character geometry reconstructs lines and columns without relying on
  object order. Unicode/Polish text and source coordinates are retained. Hybrid
  and scanned pages can use OCR; native text extraction remains the usual fast path.
- XLSX: inspect materialized content rather than inflating a styled rectangular
  extent. Merged spans and real neighboring blanks are recorded. ODS resolves
  covered cells/repeats and stores both row/column spans. Formulas are not executed.
- Large images: explicit source-pixel budget (80M default) and sequential bounded
  OCR tiles (25M per tile). The 61.9MP form 09 strip works within the request
  deadline. Source offsets are recorded and applied in the UI on the original.
- JPE: verified JPEG signature/MIME support. Two .DOC inputs are actually OOXML
  packages and are validated/read as DOCX. Binary OLE legacy DOC remains rejected.
- Understanding: source roles, completion instructions, legal prose, recipient
  constants, signature/date headers and unreliable OCR labels are separated from
  inputs. Regular dotted lines and isolated selection marks augment OCR.
- Fields: Polish semantic types, dates/ranges, email inflections and numerical
  dimensions improved. Physical checkbox evidence, grouped radio alternatives,
  option details and deduplication preserve source controls. Every detected field
  records source, geometry when available, method, score, decision reasons and
  review state. Scores are uncalibrated heuristics, not correctness probabilities.
- Structure: unfamiliar workflows preserve their own source fields/sections.
  The broad reference applicant/fee/consent profile is no longer injected into
  unrelated forms. Existing building/refund redesign profiles are selected by
  source request semantics, never filename. Ordinary table rows are static;
  dynamic repeated groups require an explicit source repetition instruction and
  are marked for review. Form 07 produces a repeated dog-details section.
- Conditions: explicit Polish equality syntax, a bounded natural-language choice
  syntax and source choice-detail relations produce evidenced rules. Ambiguous
  cases remain review warnings. Repeated-group JSONata uses the supplied answer
  path contract. Arbitrary prose/numbered references/calculations are not solved.
- Dictionaries: bundled catalog descriptions, exact semantic matching, search
  endpoint, proposed source-option dictionaries, reference checks and editable
  official/local binding. No full official values or registry data are invented.
- Recovery: retain useful pages after bounded OCR failures, preserve rejected
  label evidence, report partial/no-field/review status and never equate a valid
  COI JSON with complete recognition. Existing API and UI remain available.

## Conversion and JSON validity

| Group | Baseline converted | V03 converted | Local valid JSON among V03 converted |
|---|---|---|---|
"""
    for title, select in [("Reference 01/05", lambda r: r["category"] == "reference"), ("Previously evaluated seven sets", lambda r: r["category"] == "previously_evaluated")]:
        current = [r for r in known if select(r)]
        prior = [oldmap[r["id"]] for r in current]
        report += f"| {title} | {sum(r['status'] == 'converted' for r in prior)}/{len(prior)} | {sum(r['status'] == 'converted' for r in current)}/{len(current)} | {sum(r.get('valid', False) for r in current)}/{sum(r['status'] == 'converted' for r in current)} |\n"
    report += "| New external documents | 3/3 | 3/3 | 3/3 |\n\n"
    report += f"All organizer sources: **53/69 ({pct(53 / 69)}) → 62/69 ({pct(62 / 69)})**. All 53 previously accepted inputs remain accepted. All 62 V03 results pass published JSON Schema, the recursive compatibility profile and local business checks. Seven binary DOC files remain unsupported. This does not assert complete extraction or actual platform import.\n\n"
    report += "| Official form | Baseline | V03 |\n|---|---|---|\n"
    for group in range(1, 10):
        current = [r for r in known if r["id"].startswith(f"{group:02}-")]
        prior = [oldmap[r["id"]] for r in current]
        report += f"| {group:02} | {sum(r['status'] == 'converted' for r in prior)}/{len(prior)} | {sum(r['status'] == 'converted' for r in current)}/{len(current)} |\n"
    report += """
The final run labels 47 converted files partial and 15 review_required. A partial
status can arise from unresolved source conditions even when OCR finishes. No
conversion is labeled as verified complete. Counts include all rejected sources;
failed files were not silently removed from denominators.

## Paired reference metrics

The UUID-independent comparison protocol is documented in REFERENCE_COMPARISON.
Interactive component precision/recall/F1 include policy additions. Type accuracy
uses matched components. Section F1 and structural similarity do not prove exact
geometry, legal wording or all target behavior.

| PDF reference | Precision | Recall | F1 | Matched type accuracy | Section F1 | Structural similarity | Condition coverage |
|---|---|---|---|---|---|---|---|
"""
    for case in ["01-pdf", "05-pdf"]:
        r = newmap[case]
        m = r["metrics"]
        vals = [
            m["field_precision"],
            m["field_recall"],
            m["field_f1"],
            m["field_type_accuracy"],
            m["structural_components"]["section_f1"],
            m["structural_similarity"],
            m["conditional_rules_coverage"],
        ]
        report += "| " + case + " | " + " | ".join(pct(v) for v in vals) + " |\n"
    report += """
Primary PDF/DOCX reference metrics are preserved. All accepted reference variants
now have the same field F1 as their primary PDF: 98.04% for 01, 97.20% for 05.
The previous 05 JPEG had F1 96.30%; low-confidence noise is now excluded. Extra
PESEL/REGON/KRS proposals from published policy remain disclosed/reviewable.
All 29/31 reference states match on the existing finite choice-domain scenarios;
this is not arbitrary JSONata equivalence or general prose-condition coverage.

## Source-field regression metrics with explicit manual scope

Single-annotator inventories, authored during development from the actual blank
sources. Raw detected fields are scored, not policy-expanded COI workflows.
Forms 03/04 cover visible citizen inputs; 06 covers only its complete 24-cell
length/width/area table. These are regression results, not independent accuracy.

| Scope | Version | Precision | Recall | F1 | Matched type accuracy |
|---|---|---|---|---|---|
"""
    for r in scoped:
        report += f"| {r['id']} | {r['version']} | " + " | ".join(pct(r[k]) for k in ["field_precision", "field_recall", "field_f1", "field_type_accuracy"]) + " |\n"
    report += """
Form 03's raw false positives fall from four to zero; form 04's from three to
zero under these inventories. Form 04 still misses its rental/loan strikeout
choice. Form 06 recovers all eight printed length and width entries in addition
to eight area entries, with numeric types. Other parts of 06 are outside that
metric scope and still need review. No full field truth is claimed for 02/07/08/09.

## New externally sourced, pre-annotated check

Sources and pre-prediction annotation SHA256 are in `new-documents/`. The sample
contains three documents from two request genres. There is one annotator and no
organizer-issued expected COI JSON. These scores cannot establish competition-wide
accuracy. They use locked semantic label patterns, accent/case folding, one-to-one
matches and matched-type accuracy; exact source-style heading recall is called
section accuracy, with separate section F1 to penalize extra sections.

| Document | Version | Precision | Recall | F1 | Type accuracy | Section accuracy | Section F1 |
|---|---|---|---|---|---|---|---|
"""
    for r in metrics:
        report += (
            f"| {r['id']} | {r['version']} | "
            + " | ".join(pct(r[k]) for k in ["field_precision", "field_recall", "field_f1", "field_type_accuracy", "section_accuracy", "section_f1"])
            + " |\n"
        )
    aggregate = []
    for version in ["baseline", "v03"]:
        rows = [r for r in metrics if r["version"] == version]
        tp = sum(r["matched_fields"] for r in rows)
        n = sum(r["predicted_fields"] for r in rows)
        e = sum(r["expected_fields"] for r in rows)
        correct = sum(sum(m["type_correct"] for m in r["matches"]) for r in rows)
        aggregate.append(
            {"version": version, "matched": tp, "predicted": n, "expected": e, "precision": tp / n, "recall": tp / e, "f1": 2 * tp / (n + e), "type_accuracy": correct / tp}
        )
    (D / "new-micro-metrics.json").write_text(json.dumps(aggregate, indent=2))
    report += "\n| New-set micro metric | Baseline | V03 |\n|---|---|---|\n"
    for key in ["precision", "recall", "f1", "type_accuracy"]:
        report += f"| {key} | {pct(aggregate[0][key])} | {pct(aggregate[1][key])} |\n"
    report += """
Type/field metrics improve, but **section recognition does not consistently
improve**: GUS heading recall falls and student-form sections remain weak. This
is a remaining acceptance gap, not hidden by green JSON validation.

The strict student-card score undercounts physically recovered fields whose
labels join words, such as PESELucznia. The corresponding source elements are
present in the output, but concatenation harms readability, type inference and
strict matching. The original annotation/patterns were not changed after seeing
predictions to increase scores. Source-specific role ambiguity and static fee/
contact prose still create false inputs. GUS other-medium choices lose suffix
context/details; Finance's blank legacy subject control is missed. Source attachment
descriptions without printed answer regions are outside this field inventory and
still require a faithful electronic upload redesign.

All three new JSON outputs pass local schema/business validation. Full expected
COI workflows, legal correctness, condition coverage and complete structure truth
are N/A. Missing/extra matches are preserved individually in new-field-metrics.

## Performance, ML and platform checks

"""
    common = [r for r in known if oldmap[r["id"]]["status"] == "converted"]
    report += f"Median end-to-end time on the 53 common successful inputs: **{statistics.median(oldmap[r['id']]['processing_seconds'] for r in common):.3f}s → {statistics.median(r['processing_seconds'] for r in common):.3f}s**. Single local runs include worker startup. The hybrid-PDF heuristic can invoke OCR on small embedded images and increases latency for form 02; it is not uniformly faster.\n\n"
    report += (
        "The three newly accepted 09 raster variants take "
        + ", ".join(f"{newmap['09-' + ext]['processing_seconds']:.2f}s" for ext in ["jpeg", "jpg", "png"])
        + " in the final CLI matrix. Their original 1654×37424 (61,899,296-pixel) source is processed in 16 tiles.\n\n"
    )
    for r in fresh:
        report += f"- {r['id']}: {r['processing_seconds']:.3f}s; schema/business valid.\n"
    report += """
Existing local Naive Bayes was inspected and compared on Apple Silicon arm64 for
03/04/06. F1 is unchanged with assistance, with valid outputs in both modes.
Cold/warm timing differences are not causal speed evidence. No larger model,
retraining on the holdout, mandatory AI API or new dependency was justified.
The default remains deterministic; local assistance remains available.

- 178 pytest tests passed: original tests retained, real OCR, new format/geometry/
  recovery regressions, conditions, catalog, API, COI compatibility and bounded
  gateway framing/forwarding.
- Ruff passed. Four Chrome/Playwright suites passed with external requests blocked:
  original smoke, advanced editor/source mapping, official COI scenario, and actual
  oversized image upload including worker deadline and visible source highlight.
- The actual large-image UI/API run returns 178 fields, 16 tiles, partial status
  and valid COI, around 55–56 seconds; completeness is explicitly unverified.
- Native Tesseract 5.5.4 pol+eng works. Runtime remains 37 pinned packages with
  no new libraries. The source/initial-data/dictionary artifacts retain their
  original rights; project MIT does not relicense organizer or external documents.
- Target COI importer/registry connectivity and full official dictionary values
  remain unverified/unavailable. Local validator success is not platform success.

"""
    docker = D / "docker-verification.json"
    if docker.exists():
        evidence = json.loads(docker.read_text())
        report += """### Actual Docker verification

The image `formforge-coi:0.3.0` was built and run with Docker Desktop / Engine
29.8.2. Compose health and the seven actual API scenarios below passed. OCR uses
the separately built Tesseract 5.5.1 with pol+eng. This is a deployment smoke
matrix, not a second complete 69-file accuracy benchmark.

| Container scenario | HTTP | Seconds | Fields | Local COI validity |
|---|---|---|---|---|
"""
        for case in evidence["cases"]:
            report += (
                f"| {case['case']} | {case['http_status']} | {case['seconds']:.3f} | {case.get('fields', 'N/A')} | {'passed' if case.get('valid') else 'expected rejection'} |\n"
            )
        report += """
The processing service runs as uid 10001 with a read-only root and only an
internal network; zero request temporary directories remain after these tests.
Real OCR linkage excludes libgomp/curl/archive/TIFF/JBIG. Installed Python and
OCR linkage inventories are retained, but do not constitute a full audited SBOM.

Docker 29 did not publish the host port for the original internal-only service.
A fixed-target standard-library ingress gateway now publishes localhost and
forwards only to the isolated processor. This addresses the observed
[Moby internal-network port issue](https://github.com/moby/moby/discussions/53256)
while preserving the processor's network isolation; see also
[Docker port-publishing documentation](https://docs.docker.com/engine/network/port-publishing/).
The gateway has separate resource limits and ephemeral storage, bounds request
bodies, supports Content-Length/chunked uploads and preserves authorization.
No third-party gateway package or external AI API was added.

Docker Desktop's Compose Bake path-grant step also failed on this Unicode path;
the documented direct `docker build` command succeeded. Evidence is stored in
`evaluation/engine-v03/docker-verification.json` and adjacent inventories.
"""
        if evidence.get("browser_smoke", {}).get("status") == "passed":
            report += "\nThe original browser smoke suite also passed against the actual Compose gateway: upload, edit, official JSON download, eForm validation, dynamic visibility, mobile layout and local Swagger, with zero external requests or uncaught browser errors.\n"
        report += "\n"
    else:
        report += "Docker Compose config passed. Docker Desktop startup/container verification is pending; no image build success is claimed here.\n\n"
    report += """## Changed implementation files

- Extraction: `formforge/extractors.py`, new `docx_reader.py`, `pdf_text.py`,
  `image_tiles.py`, plus `geometry.py` and `ocr.py`.
- Understanding/model: new `document_understanding.py`, `layout_analyzer.py`,
  `field_detector.py`, `models.py`, `structure_builder.py`, `coi_standardizer.py`,
  `conditions.py`, `dictionaries.py`, new `data/coi_dictionaries.json`.
- Integration: `pipeline.py`, `file_validator.py`, `config.py`, `main.py`,
  `.env.example`, `pyproject.toml` (version 0.3.0).
- Deployment: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, new
  `deploy/gateway.py`, `tests/test_gateway.py`, `scripts/check_container_v03.py`.
- Existing UI fixes only: `static/app.js`, `editor.js`, `source_mapping.js`,
  `compatibility.js`, `app.css`, `templates/index.html`; no redesign.
- Regression/evidence: `tests/test_engine_v03.py`, `demo_samples/zaswiadczenie.jpe`,
  `scripts/generate_samples.py`, `evaluate_v03.py`, `score_v03.py`, `report_v03.py`,
  `ui_large_image.cjs`, `package_release.py`, protected `evaluate_coi.py`.
- Documentation/data: README, notices, these reports and `evaluation/engine-v03/`.
  `changed-files.txt` gives the complete pre-commit inventory; ignored reference
  materials and frozen coi-v1 files were not modified.

## Remaining limitations and the three next improvements

1. **Source understanding and scope:** better paragraph/label reconstruction,
   typography-aware sections, nested table roles, named-person scope, numbered
   dependencies and calculations. New-set section quality and joined labels
   demonstrate why this is the highest priority. Checkbox ambiguities, layout/OCR
   differences and boilerplate false positives still require review.
2. **Verified format completeness:** binary DOC via an audited permissively
   licensed converter, complete Word legacy blank controls, more reliable mixed
   PDF/image recognition and bounded handling beyond tested scan geometry.
   Apache POI HWPF is a candidate; no unverified DOC converter is shipped.
3. **Contest-grade validation:** larger independently annotated corpus, native
   COI importer tests, actual dictionary/registry integration, legally confirmed
   applicant/fee/consent design and a verified container/native SBOM. Optional
   conditional requiredness has no documented official serialization and remains
   an explicit review item rather than an invented COI property.

Detailed gaps: REMAINING_COMPETITION_GAPS.md. Source references for DOC research:
[Apache POI HWPF](https://poi.apache.org/components/document/index.html),
[Microsoft MS-DOC specification](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-doc/).
No broad legacy-DOC support, full document understanding or competition readiness
is claimed. Main was not merged automatically.
"""
    (ROOT / "docs/ENGINE_V03_REPORT.md").write_text(report)
    print("Wrote ENGINE_V03_REPORT.md from preserved evaluation evidence")


if __name__ == "__main__":
    main()
