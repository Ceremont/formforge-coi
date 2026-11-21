> **1.0:** aktualna macierz: [COI_REQUIREMENTS_MATRIX.md](COI_REQUIREMENTS_MATRIX.md), [FINAL_COMPETITION_REPORT.md](FINAL_COMPETITION_REPORT.md). 68/69 konwersji lokalnie poprawnych, importer niezweryfikowany, DOC/warunki/słowniki częściowe. Poniżej zachowany opis kontraktu i historyczne wyniki.

# COI compatibility and quality report

> This report preserves the COI-v1 contract and measurements. Current 0.3 engine
> metrics, container verification and remaining gaps are in
> [ENGINE_V03_REPORT.md](ENGINE_V03_REPORT.md). The frozen coi-v1 data is unchanged.

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
| 02 | 2 | 23 / 66 | 0.256 | 6/8 | 6/6 |
| 03 | 1 | 8 / 37 | 0.185 | 7/8 | 7/7 |
| 04 | 1 | 12 / 39 | 0.187 | 7/8 | 7/7 |
| 06 | 2 | 26 / 70 | 0.243 | 7/8 | 7/7 |
| 07 | 2 | 39 / 55 | 0.270 | 4/6 | 4/4 |
| 08 | 6 | 60 / 88 | 0.581 | 5/8 | 5/5 |
| 09 | 16 | 85 / 80 | 0.439 | 4/8 | 4/4 |

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
| 02 | doc | doc_not_supported | 415 |
| 02 | docx | no_text | 422 |
| 03 | doc | doc_not_supported | 415 |
| 04 | doc | doc_not_supported | 415 |
| 06 | doc | doc_not_supported | 415 |
| 07 | doc | doc_not_supported | 415 |
| 07 | jpe | unsupported_format | 415 |
| 08 | doc | doc_not_supported | 415 |
| 08 | docx | no_text | 422 |
| 08 | xlsx | cell_limit | 413 |
| 09 | doc | doc_not_supported | 415 |
| 09 | jpeg | invalid_document | 422 |
| 09 | jpg | invalid_document | 422 |
| 09 | png | invalid_document | 422 |

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
