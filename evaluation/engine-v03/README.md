# FormForge 0.3 evaluation

- `baseline.json`: baseline commit and SHA256 of all 140 frozen coi-v1 files.
- `known-results.json`: final rerun of all 69 official source files. Forms 01/05
  are paired references; the other seven sets are previously evaluated development
  and regression inputs, not a new independent test.
- `results/`, `exports/`, `comparisons/`: complete outputs, raw detections, source
  evidence, COI validation and UUID-independent reference comparisons.
- `annotations-known.json`, `annotated-known-metrics.json`: single-annotator
  development regression inventories with explicit scope. Form 06 scores only its
  24-cell dimensions table. No full-corpus ground truth is invented.
- `new-documents/`: three externally sourced government blanks, original source
  URLs/SHA256, annotations written before predictions, and annotation lock.
- `baseline-new/`, `baseline-new-results.json`: the original Git commit 744fc19
  run against the same new inputs in a temporary exported checkout.
- `new-results.json`, `new-field-metrics.json`: prospective external results with
  strict preregistered label-pattern matching; these also measure label usability,
  not only physical region discovery. Full official COI truth is unavailable.
- `engine-freeze.json`: final runtime hashes. R1 preceded external source selection;
  a final revision changed only OCR-noise filtering after inspecting known 01/05.
  Source annotations preceded predictions. No engine change used new outcomes.
- `engine-freeze-r1-development.json`, `development/`, `trials/`: development
  history. Exploratory matrices can overlap edits; do not cite them as the final
  fixed-engine run.
- `ml-ablation.json`: small Apple Silicon comparison of existing optional local
  classifier; no demonstrated F1 gain and no claim of causal speed improvement.
- `docker-verification.json`, `container-python-inventory.json`,
  `container-ocr-linkage.txt`: actual built-image API/OCR, process identity,
  filesystem/network isolation and request-temp cleanup checks. Inventories are
  not a full audited native SBOM. `verification.json` records the final QA gates.

The engine freeze covers runtime Python under `formforge/` and bundled data.
Later source-preview fixes and Docker ingress/deployment work do not change
recognition or the frozen metrics. Deployment is tested separately. The complete
pre-commit source/evidence inventory is in `changed-files.txt`.

Metrics are scoped, single-annotator, single-run measurements. The external set
has three documents and two request genres. It cannot establish competition-wide
accuracy. Run `python scripts/evaluate_v03.py known`, then `new`, then
`python scripts/score_v03.py`. Preserve active freeze/annotations. Further engine
changes require a new version and new unseen documents.
