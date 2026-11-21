"""Render factual quality reports from the preserved evaluation records."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evaluation/coi-v1"


def read(name):
    return json.loads((EVAL / name).read_text())


def pct(value):
    return f"{value * 100:.2f}%"


def main():
    refs, independent = read("references-results.json"), read("independent-results.json")
    # Correct an instrumentation flag using the already preserved extraction
    # evidence. No conversion or prediction is modified by this correction.
    for records, name in [(refs, "references-results.json"), (independent, "independent-results.json")]:
        for record in records:
            if record["status"] == "converted":
                result = read(f"results/{record['group']}-{record['extension']}.json")
                record["ocr"] = bool(result["document"]["analysis"].get("ocr"))
        (EVAL / name).write_text(json.dumps(records, ensure_ascii=False, indent=2))
        for group in {r["group"] for r in records}:
            (EVAL / (group + "-results.json")).write_text(json.dumps([r for r in records if r["group"] == group], ensure_ascii=False, indent=2))
    report = """# Reference comparison: official development scenarios 01 and 05

These two paired cases were used to develop the algorithm. They are not an
independent test. Source inputs were extracted automatically, including PDF,
DOCX, spreadsheets and OCR images. Conversion never loads an expected JSON or
branches on the filename. Raw detections, policy-normalized forms and exports
are preserved separately in `evaluation/coi-v1/results/` and `exports/`.

## Method and metric limits

- Interactive fields: exclude SECTION, REPEATING_SECTION, TEXT_BLOCK and
  INFO_SECTION; include CONSENT_SECTION. A country/TERYT cascade is one component,
  not the number of its implied address attributes.
- Match one-to-one inside semantically matched sections. Fold Polish spelling,
  normalize filler words and the documented authorization typo; TERYT variants
  share an address-cascade role, while exact dictionary identity is compared
  separately. An unambiguous single upload/consent/text component may match by
  its role within its section. All pairs and scores are recorded for audit.
- Precision = matched/generated; recall = matched/reference; F1 is the harmonic
  mean. These measure the resulting COI proposal, including policy additions,
  **not raw OCR accuracy**. Type accuracy uses matched interactive fields only.
- Visual reading order uses grid y/x, not JSON array order. Structural similarity
  averages section-title F1, within-section pairwise order concordance, tab-type
  sequence similarity and indexed flow-edge Jaccard. It does not score exact
  geometry, FINISH styling, validations, legal text or title wording.
- Conditional coverage compares each matched reference state by executing both
  JSONata expressions over choice domains plus an unanswered value. Countries
  use Polska and a non-Polska value. At most 256 combinations per expression.
  This is finite-domain behavior checking, not a proof of arbitrary JSONata
  equivalence. Unsupported/missing expressions count as uncovered.
- Times are seconds per file, including worker startup and comparison, single
  local run. They are not latency percentiles or load-test results.

## Primary PDF results

| Form | Matched / expected / generated inputs | Precision | Recall | F1 | Type accuracy | Structure | Conditions | Schema + business | Seconds |
|---|---|---|---|---|---|---|---|---|---|
"""
    for group in ["01", "05"]:
        r = next(r for r in refs if r["group"] == group and r["extension"] == "pdf")
        m = r["metrics"]
        report += f"| {group} | {m['matched_fields']} / {m['expected_interactive_fields']} / {m['generated_interactive_fields']} | {pct(m['field_precision'])} | {pct(m['field_recall'])} | {pct(m['field_f1'])} | {pct(m['field_type_accuracy'])} | {pct(m['structural_similarity'])} | {pct(m['conditional_rules_coverage'])} | pass | {r['processing_seconds']:.3f} |\n"
    report += """
Both source DOCX cases have the same semantic field metrics as their PDFs.
Form 01 has no unmatched reference inputs. It adds two policy PESEL fields:
applicant and represented person. Form 05 adds REGON/KRS for the company and
PESEL for the represented person. These are marked policy proposals requiring
confirmation; extra fields lower precision rather than being hidden from scores.

All 29 states of 01 and 31 states of 05 matched on the tested answer domains.
There are zero unrecognized reference JSONata expressions in this check. This
does not mean arbitrary prose conditions in unknown documents are recognized.

## Differences that the summary scores deliberately do not hide

| Property on matched inputs | Form 01 differences | Form 05 differences |
|---|---|---|
"""
    comparisons = {}
    for group in ["01", "05"]:
        comparisons[group] = read(f"comparisons/{group}-pdf.json")
    for key in ["type", "validation", "dictionaryName", "defaultValue", "readOnly"]:
        counts = [sum(key in m["differences"] for m in comparisons[g]["matches"]) for g in ["01", "05"]]
        report += f"| {key} | {counts[0]} | {counts[1]} |\n"
    report += """
Option label/order differences on matched inputs: zero in both primary cases.
One address dictionary differs: generated TERYT_4G_DOWODOWY follows the supplied
design standard instead of TERYT_DOWODOWY in that reference field. The other
address cascades match. Registry bindings follow the initial-data contract;
readOnly is enforced. Required/typed validation follows technical/design rules,
whereas most reference validators are empty. The original `validation:{}` values
are diagnosed, not copied. Consent text is a review placeholder without an
invented legal URL, and consent is optional until confirmed; this intentionally
differs from required consent in the reference. No reference legal prose is
copied into generated results as a substitute for recognition.

Both output flows have three forward links between four pages. Contact page
wording is normalized to Kontakt i zgody. FINISH uses INFO_SECTION as required
by technical rules, while both supplied examples use SECTION/TEXT_BLOCK.
Source title wording can remain abbreviated relative to the reference title.
These differences prevent a claim of exact reference or platform equivalence.

## All source formats in the development set

| Form | Format | Result | Fields in model | Precision | Recall | F1 | Type | Structure | Conditions | Seconds |
|---|---|---|---|---|---|---|---|---|---|---|
"""
    for r in refs:
        if r["status"] == "converted":
            m = r["metrics"]
            vals = [pct(m[k]) for k in ["field_precision", "field_recall", "field_f1", "field_type_accuracy", "structural_similarity", "conditional_rules_coverage"]]
            report += f"| {r['group']} | {r['extension']} | valid; review required | {r['fields']} | " + " | ".join(vals) + f" | {r['processing_seconds']:.3f} |\n"
        else:
            report += f"| {r['group']} | {r['extension']} | {r['error']['code']} | — | — | — | — | — | — | — | {r['processing_seconds']:.3f} |\n"
    report += """
13/15 supplied source files converted; all 13 pass local schema, recursive
profile and business checks. The two DOC files intentionally return 415.
Spreadsheet/OCR differences are reported per format and are not replaced by
PDF results. Many digital standard fields cannot be extracted literally from
the paper; they are policy-driven additions with provenance and review status.

Evidence: `evaluation/coi-v1/comparisons/*` includes every matched/missing/extra
component, validation/default/dictionary differences and each reference query
with its generated counterpart and test result. `*-reference-validation.json`
diagnoses the organizer examples themselves. `docs/coi-source-manifest.json`
allows byte-level integrity checking of originals.
"""
    (ROOT / "docs/REFERENCE_COMPARISON.md").write_text(report)
    report = """# COI compatibility and quality report

Current status: **official-format proposal, review required; platform import
unverified; not competition-ready**. This extends the existing project rather
than replacing it. No external AI API, model download or runtime network lookup
is used.

## Implemented contract

COIFormAdapter maps the internal editable model to `title/tabs/flow`, MAIN and
last FINISH, UUID page/field/link IDs, single-level SECTION/REPEATING_SECTION,
three-column grid bounds, the supplied COI field types, explicit validation,
options or dictionaryName, defaultValue/EXTERNAL_SYSTEM, SHOW/READ_ONLY JSONata,
forward page links and a direct INFO_SECTION finish component. Option IDs remain
strings as in official examples. Generic repeated groups map to root repeating
sections, preserving children without illegal nested sections.

Raw published JSON Schema validation is separate from a recursive Pydantic
compatibility profile and technical rules: nonempty pages/sections, mandatory
properties, no nesting, input placement, finish restrictions, validators,
dictionaries, registry bindings, UUID uniqueness, grid overlaps, reachability,
links and generated JSONata references/syntax. The canonical output grid key is
repeatingSectionGrid; the misspelled schema alias is accepted at input with a
warning. The schema copy and supplied files remain byte-for-byte unchanged.

The UI exports the official root directly and has Zgodność z COI diagnostics,
provenance and property confirmation. The old preview format remains available
explicitly. File processing, editing, preview and validation API routes remain
available; raw COI validation and schema routes are added.

## Independent test protocol and results

Engine hashes were frozen in `evaluation/coi-v1/engine-freeze.json` after learning
from spec and 01/05, before predicting 02/03/04/06/07/08/09. Runtime has no reference
JSON lookup. Inputs were passed to workers as `unknown.<extension>` to prevent
filename selection. No recognition-engine change was made after inspecting these
results. The evaluation script checks the freeze before an independent run.

There is no official expected FormDefinition for these seven cases. Consequently
full field precision/recall/F1, type accuracy, structural similarity and
conditional coverage are **N/A**, recorded as null, rather than guessed or
inferred from a green validator. A complete manual annotation is still needed.
Source review below is a qualitative post-run audit, not a scored benchmark.

| Form | PDF pages | Raw detected / final model fields | PDF seconds | All supplied files converted | Valid COI among converted |
|---|---|---|---|---|---|
"""
    for g in ["02", "03", "04", "06", "07", "08", "09"]:
        group = [r for r in independent if r["group"] == g]
        r = next(r for r in group if r["extension"] == "pdf")
        result = read(f"results/{g}-pdf.json")
        converted = sum(r["status"] == "converted" for r in group)
        valid = sum(r.get("valid", False) for r in group)
        report += f"| {g} | {len(result['form']['pages'])} | {r['raw_fields']} / {r['fields']} | {r['processing_seconds']:.3f} | {converted}/{len(group)} | {valid}/{converted} |\n"
    report += """
All 40 converted independent files pass the supplied schema, recursive profile
and local business checks; 40/54 supplied files converted overall. This is a
format-validity result, not 100% recognition accuracy. The matrix includes DOC
and other rejected inputs so success is not inflated by dropping failures.
OCR actually ran on the accepted raster inputs; textual PDFs used extraction.

## Observed information losses and false detections

| Form | Material gaps found in source review |
|---|---|
| 02 | Refund method cash/transfer remains prose, not a reliable choice; date of original payment and representative address lose structure; instructions/headings become textarea candidates. DOCX uses drawing/text-box content and returns no_text. |
| 03 | Five certificate-purpose checkboxes are not recovered as a proper choice/options group. Other-purpose and submission-purpose blanks survive, but no correct Other SHOW dependency. INFORMACJE can become a false input. |
| 04 | End of rental interval after “do” is lost; start is generic text rather than a date. Rental/loan strikeout choice and responsible-person condition are not modeled. Paper place/date may remain an unwanted input. |
| 06 | Repeated length/width/area triplets lose length and width components; eight “razem” values are ambiguous text. Road identifier, work dates and attachment conditions are incomplete; fragments of legal/instruction prose become inputs. |
| 07 | Dog sex and chip/tattoo/none controls become fragmented text instead of choices with dependent identifiers. Dog details do not become a confirmed dynamic repeating group; descriptive conditions and some address prose lose structure. Privacy fragments/office account can become inputs. |
| 08 | Six-page tax declaration is overgeneralized by the building-content profile. Spouse-specific fields, numbered address scopes, composting/annex conditions and calculated fee totals are not faithfully represented; legal text and fixed recipient data create false inputs. No arithmetic formulas are generated. |
| 09 | Sixteen-page bundle contains three different applications plus repeated athlete/coach/minor consent sections. The output does not split them into faithful workflows; applicant/person names and scopes are conflated, sports checkbox lists, ePUAP/eDelivery fields, consent branches and pupil repeats are incomplete. |

The above were not repaired using this same independent set and then reported as
an independent success. They define the next development backlog. New unseen
forms will be needed to evaluate any such changes fairly.

## Unrecognized conditions

Reference 01/05: zero unrecognized expressions in the 29/31 finite-domain
JSONata comparisons. The exporter compiles a bounded internal equality/inequality
and AND/OR tree, simple explicit source rules and policy templates. It does not
translate arbitrary natural-language rules into arbitrary JSONata.

Unrecognized source dependencies include: 02 transfer -> account/owner; 03 Other
-> extra purpose; 04 different responsible person -> consent attachment; 06
traffic impact -> traffic plan and work-security alternatives; 07 chip/tattoo
-> identifier plus multiple dogs; 08 spouse status, address overrides, annexes,
composting and fee calculations; 09 application kind, club representation,
correspondence channel, sport family and adult/minor/pupil consent branches.
No exact percentage is claimed for these without a full condition annotation.

## Rejected files and runtime limits

| Form | Format | Code | HTTP-equivalent status |
|---|---|---|---|
"""
    for r in independent:
        if r["status"] != "converted":
            e = r.get("error", {})
            report += f"| {r['group']} | {r['extension']} | {e.get('code', r['status'])} | {e.get('status', '—')} |\n"
    report += """
DOC lacks a verified permissively licensed converter; JPE is not an accepted
extension. DOCX 02/08 contain meaningful text inside drawing/text-box structures,
not normal paragraphs/tables supported by this extractor. XLSX 08 exceeds the
30,000-cell safety budget. Images 09 are 1654×37424 (61,899,296 pixels), beyond
the configured limit; the existing image error wrapper reports invalid_document
rather than a precise pixel-limit message. Their PDF/DOCX alternatives were
still evaluated. Limits were not raised after seeing independent failures.

Complete per-file timings, SHA256, OCR flags, diagnostics and output paths are
in `evaluation/coi-v1/independent-results.json`; all successful exports and
internal/raw models are included. Processing time includes Python worker startup.

## Validation and remaining readiness work

- 146 pytest tests passed, including real OCR, API/backwards compatibility,
  mandatory business constraints, legacy grid alias, malformed COI input,
  repeating-section JSONata and official PDF/DOCX scenarios. Ruff passed.
- Three local Chrome/Playwright suites passed: original upload/edit/validation,
  advanced editor/source mapping, and official 05 compliance/conditions/edit/
  download/raw validation. All remote requests were blocked; zero attempted
  external requests and zero uncaught browser errors were recorded.
- Local Tesseract 5.5.4 with pol+eng worked. Runtime dependency lock now includes
  37 packages; JSONata interpreter is Apache-2.0. Organizer materials retain
  their original rights/terms, not the project MIT license.
- `docker compose config --quiet` passed. Docker daemon socket is absent, so
  image build, container execution and native SBOM remain unverified.
- No actual COI importer test, registry connectivity or full dictionary dataset
  is available. Local preview has no platform registry values or full TERYT tree,
  and does not implement dynamic repeated-row editing like the target engine.
- Consent text/URLs, applicant roles, fees and extra standard fields need human
  confirmation. Generic profiles can be inappropriate for unfamiliar workflows.
- Internal min/max/length/phone rules and conditional requiredness are not all
  expressible through the supplied COI validator codes; review diagnostics keep
  unsupported explicit rules instead of inventing official keys. Local server
  value checks and native input constraints do not imply equal platform behavior.
- Next: expand general layout/table and drawing/text-box extraction, typed choice
  and subject-scope recognition, legally review workflow/consents/dictionaries,
  annotate a new independent corpus, test importer behavior and build the image.

Run commands are in README.md. Reproduce: `python scripts/evaluate_coi.py references`,
`python scripts/evaluate_coi.py independent`; preserve the existing freeze and
results when starting a new engine version. Older synthetic holdout numbers and
preview-phase readiness/defense documents are historical and superseded.
"""
    (ROOT / "docs/COI_COMPATIBILITY_REPORT.md").write_text(report)
    print("Wrote both COI reports from preserved evidence")


if __name__ == "__main__":
    main()
