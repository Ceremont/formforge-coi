> **1.0:** analiza oryginałów pozostaje aktualna; końcowe wdrożenie i statusy wymagań: [COI_REQUIREMENTS_MATRIX.md](COI_REQUIREMENTS_MATRIX.md). Oryginały niezmienione; nie są redystrybuowane w czystej paczce.

# Official COI source analysis

The user supplied `COI_HackNation_official_reference_pack.zip`; the advertised
reference directory was absent, so its 82 entries were imported safely to
`reference/coi-official/` without altering their bytes. Source hashes are in
`coi-source-manifest.json`. Only specifications and reference scenarios 01/05
are development inputs. Scenarios 02/03/04/06/07/08/09 are reserved for a frozen
post-development check; filenames alone are not model features.

## Authoritative structure

Root keys: `title`, `tabs`, `flow`. A tab has `id`, `title`, `type` (MAIN/FINISH),
`questions`. A question is grid placement `x,y,rows,cols` plus `field`. A field
uses `id,type,techName,title,description,options,validation,readOnly`, nested grid,
`states`, `questionOrder`, `tooltipMessage`, optional defaults/dictionaries.
SECTION/REPEATING_SECTION are page-level containers; input fields belong inside
one container. Sections cannot nest. The technical FINISH exception allows
INFO_SECTION only. Flow links connect page IDs; output identifiers are UUIDs.
Reference option IDs are human-readable strings, not UUIDs, and JSONata refers
to their answer values. Thus UUID requirements apply to pages/fields/links,
while option IDs remain opaque string values compatible with the examples.

## Source discrepancies (originals remain untouched)

1. Schema/description use **repetingSectionGrid**; both configuration examples
   and technical JSONata use **repeatingSectionGrid**. Output uses the latter;
   legacy input spelling is recognized explicitly. Raw-schema validation and a
   recursively checked compatibility profile are reported separately.
2. The supplied schema has no root `required`, allows unknown properties and
   does not recursively validate actual nested grids. Even `{}` passes it.
   Schema validation alone cannot establish import readiness.
3. Examples use SECTION containing TEXT_BLOCK on FINISH; technical rules require
   INFO_SECTION only. Generated output follows the technical rule. Reference
   failures are reported instead of silently rewriting their JSON.
4. Example 01 contains three `validation: {}` objects instead of arrays. Most
   input validators in both references are empty despite mandatory/typed
   validators in the standards. Generated validators follow the technical list.
5. Reference 05 flow link IDs are short strings, not UUIDs. Generated IDs are UUIDs.
6. The schema declares scalar defaultValue; examples and rules use arrays on
   SELECT. Compatibility models allow type-appropriate string/array defaults.
7. Standard initial-data bindings require readOnly; some reference/contact
   examples conflict with this or use different allowed registries. The exporter
   records policy-generated bindings separately and never fetches registry data.

## Standardization versus extraction

The paper forms have far fewer fields than the digital examples. Common sections
(Twoje dane, alternate applicant/person/company, domestic/foreign address,
authorization and contact) come from the published design standards, not from
copying a reference configuration. Standard additions require visible provenance
and confirmation, particularly applicant eligibility and fees. Raw detected
fields remain available for inspection. No reference JSON is loaded by runtime
conversion and no filename selects a prepared output.

Full analysis covers the technical DOCX tables, JSON description/schema,
dictionary DOCX, initial-data PDF, 29-page design standards, both original
PDF/DOCX inputs and all 16 visualization images per reference scenario. A copy
of the unchanged published schema is bundled as `formforge/data/coi_schema.json`;
runtime does not read reference examples or the evaluation corpus.

## Adapter decisions and supported semantics

| Internal concept | Official serialization |
|---|---|
| Thematic section.coi.tab | MAIN tab; physical source page remains provenance |
| Section | SECTION at page level, child questions in repeatingSectionGrid |
| Group with repeat_key | REPEATING_SECTION at page level; never nested SECTION |
| text/email/phone/PESEL/NIP/REGON/postal/address | TEXT_FIELD; supported validator codes retained |
| textarea/number/date | TEXTAREA/NUMBER/DATEPICKER |
| checkbox/radio/select | CHECKBOX/RADIO/SELECT with answer-string option IDs |
| attachment | FILE_UPLOADER |
| information/consent | TEXT_BLOCK/CONSENT_SECTION with consents configuration |
| Field/section visibility | states SHOW with compiled JSONata |
| Static/dynamic read-only | readOnly and states READ_ONLY on input fields |
| Initial registry binding | defaultValueType EXTERNAL_SYSTEM and registry.attribute, readOnly |
| Country/address dictionaries | Kraje / TERYT names, empty options with dictionaryName |
| Completion | Last FINISH with direct INFO_SECTION |
| Page sequence | UUID flow links, forward/reachable, no outgoing FINISH |

The generated layout uses valid full-width placement and sequential grid rows.
It does not try to reproduce a paper form's exact pixel layout. UUID5 identities
are derived from form identity/component paths; equality is not evaluated by UUID.
The internal COI expression tree supports equality, inequality, AND and OR;
serialization uses official answer paths, including $repeatingSectionIndex for
repeated groups. There is no eval of document text or remote JSONata service.

The raw schema's limited recursion is retained and reported honestly. The
compatibility model accepts real-example array defaults and the correct grid
spelling, while business checks express constraints missing from the schema.
This profile is an implementation interpretation of conflicting supplied sources,
not a new organizer-issued schema or a verified target importer contract.

The standard applicant/address/representation/contact profile is selected by
source content. Subject-specific building/refund rules were developed from 01/05.
These rules are reusable phrase-based heuristics, not a general administrative
workflow parser. On unknown documents this profile can add inappropriate fields
or confuse the subject scope; the independent results document those failures.

Known source conditions and defaults are never silently represented as proven
legal rules. Provenance separates source-backed facts, published-policy additions
and manual edits. No legal URL, complete external dictionary or registry value
is invented. Fee/role/consent decisions require explicit review.
