# COI inputs: current availability

The prior preview-phase missing-input list is superseded. The user supplied the
complete official pack now preserved under `reference/coi-official/` with hashes
in `coi-source-manifest.json`. It includes the schema, description, technical
rules, dictionary descriptions, initial-data contract, design standards,
visualizations, nine source form sets and paired JSON configurations for 01/05.

Still required before claiming platform/competition readiness:

1. Access to the actual COI importer/runtime and confirmed behavior for the
   spelling/default/FINISH contradictions documented in OFFICIAL_COI_ANALYSIS.
2. Full dictionary values, versions and runtime registry access; descriptions
   alone are not a complete local dictionary dataset.
3. A complete independent annotation of 02–09 for quantitative field/type/
   structure/condition quality, plus new unseen forms for future development.
4. Confirmation of applicant eligibility, fees, consent content/links, attachment
   restrictions and institution-specific legal workflow.
5. A working Docker daemon to build/test the image and produce a native SBOM.

Current implementation and measured gaps: [COI_COMPATIBILITY_REPORT.md](COI_COMPATIBILITY_REPORT.md).
