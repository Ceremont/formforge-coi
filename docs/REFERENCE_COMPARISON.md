> **1.0:** bieżące wyniki 01/05 i pozostałych źródeł: [FINAL_ACCURACY_REPORT.md](FINAL_ACCURACY_REPORT.md). 15/15 referencji konwertuje; PDF/DOCX F1 workflow 98,04% / 97,20%, z jawnymi uzupełnieniami standardu. To development, nie niezależny test. Poniżej zachowany historyczny protokół COI-v1.

# Reference comparison: official development scenarios 01 and 05

> COI-v1 comparison protocol and historical results. Version 0.3 reruns and
> updated format coverage are in [ENGINE_V03_REPORT.md](ENGINE_V03_REPORT.md)
> and `evaluation/engine-v03/`; the original benchmark is preserved unchanged.

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
| 01 | 50 / 50 / 52 | 96.15% | 100.00% | 98.04% | 100.00% | 100.00% | 100.00% | pass | 0.542 |
| 05 | 52 / 52 / 55 | 94.55% | 100.00% | 97.20% | 100.00% | 100.00% | 100.00% | pass | 0.529 |

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
| type | 0 | 0 |
| validation | 44 | 46 |
| dictionaryName | 1 | 1 |
| defaultValue | 4 | 7 |
| readOnly | 6 | 6 |

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
| 01 | png | valid; review required | 54 | 96.15% | 100.00% | 98.04% | 100.00% | 100.00% | 100.00% | 5.245 |
| 01 | doc | doc_not_supported | — | — | — | — | — | — | — | 0.003 |
| 01 | docx | valid; review required | 54 | 96.15% | 100.00% | 98.04% | 100.00% | 100.00% | 100.00% | 0.461 |
| 01 | jpeg | valid; review required | 54 | 96.15% | 100.00% | 98.04% | 100.00% | 100.00% | 100.00% | 5.428 |
| 01 | jpg | valid; review required | 54 | 96.15% | 100.00% | 98.04% | 100.00% | 100.00% | 100.00% | 5.555 |
| 01 | ods | valid; review required | 54 | 96.15% | 100.00% | 98.04% | 100.00% | 100.00% | 100.00% | 0.447 |
| 01 | pdf | valid; review required | 54 | 96.15% | 100.00% | 98.04% | 100.00% | 100.00% | 100.00% | 0.542 |
| 01 | xlsx | valid; review required | 54 | 96.15% | 100.00% | 98.04% | 100.00% | 100.00% | 100.00% | 0.543 |
| 05 | doc | doc_not_supported | — | — | — | — | — | — | — | 0.001 |
| 05 | jpg | valid; review required | 57 | 94.55% | 100.00% | 97.20% | 100.00% | 100.00% | 100.00% | 3.016 |
| 05 | ods | valid; review required | 57 | 94.55% | 100.00% | 97.20% | 100.00% | 100.00% | 100.00% | 0.461 |
| 05 | pdf | valid; review required | 57 | 94.55% | 100.00% | 97.20% | 100.00% | 100.00% | 100.00% | 0.529 |
| 05 | png | valid; review required | 57 | 94.55% | 100.00% | 97.20% | 100.00% | 100.00% | 100.00% | 2.871 |
| 05 | docx | valid; review required | 57 | 94.55% | 100.00% | 97.20% | 100.00% | 100.00% | 100.00% | 0.483 |
| 05 | jpeg | valid; review required | 58 | 92.86% | 100.00% | 96.30% | 100.00% | 99.29% | 100.00% | 3.022 |

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
